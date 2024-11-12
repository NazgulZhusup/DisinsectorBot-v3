import asyncio
import logging
from datetime import datetime
from sqlite3 import IntegrityError

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from app.model import Disinsector, Order
from database import db
from app.utils import send_telegram_message
from config import Config
from app import create_app
from keyboards import inl_kb_accept_order, inl_kb_chemical_type, inl_kb_poison_type, inl_kb_insect_type

# Настройка логирования
logger = logging.getLogger('disinsector_bot')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('disinsector_bot.log')
stream_handler = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Определение состояний FSM
class OrderForm(StatesGroup):
    accept = State()  # Ожидание ответа на принятие заявки
    chemical_type = State()  # Выбор химиката
    area = State()  # Площадь помещения
    poison_type = State()  # Тип яда
    insect_type = State()  # Тип насекомых
    estimated_cost = State()  # Оценка стоимости

# Асинхронная функция запуска бота дезинсектора
async def start_disinsector_bot(token, disinsector_id):
    storage = MemoryStorage()
    bot = Bot(token=token)  # Здесь создаем объект bot
    dp = Dispatcher(bot=bot, storage=storage)

    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        try:
            telegram_user_id = message.from_user.id
            logger.info(f"Получен запрос на регистрацию от telegram_user_id={telegram_user_id} для дезинсектора id={disinsector_id}")

            # Получаем дезинсектора по его уникальному id, используя Session.get()
            disinsector = db.session.get(Disinsector, disinsector_id)
            if not disinsector:
                await message.answer("Ошибка авторизации. Некорректный токен.")
                logger.error(f"Дезинсектор с id {disinsector_id} не найден.")
                return

            logger.info(f"Дезинсектор найден: {disinsector.id}, {disinsector.name}")

            # Проверяем, имеет ли дезинсектор уже telegram_user_id
            if disinsector.telegram_user_id:
                if disinsector.telegram_user_id == telegram_user_id:
                    await message.answer(f"Добро пожаловать снова, {disinsector.name}! Вы уже зарегистрированы.")
                    logger.info(f"Дезинсектор {disinsector.name} ({disinsector.id}) уже зарегистрирован с telegram_user_id {telegram_user_id}")
                else:
                    await message.answer("Этот дезинсектор уже привязан к другому Telegram аккаунту.")
                    logger.warning(f"Дезинсектор id={disinsector.id} уже привязан к другому telegram_user_id={disinsector.telegram_user_id}")
                return

            # Проверяем, привязан ли telegram_user_id к другому дезинсектору
            existing_disinsector = db.session.query(Disinsector).filter_by(telegram_user_id=telegram_user_id).first()

            if existing_disinsector:
                await message.answer("Этот Telegram аккаунт уже привязан к другому дезинсектору.")
                logger.warning(f"Пользователь с telegram_user_id={telegram_user_id} уже привязан к дезинсектору id={existing_disinsector.id}")
                return

            # Привязываем telegram_user_id к текущему дезинсектору, если он не привязан
            disinsector.telegram_user_id = telegram_user_id
            logger.info(f"Попытка привязать telegram_user_id {telegram_user_id} к дезинсектору {disinsector.id}")
            try:
                db.session.flush()  # Принудительная синхронизация с базой данных
                db.session.commit()
                logger.info(f"telegram_user_id {telegram_user_id} успешно привязан к дезинсектору {disinsector.id}")
            except IntegrityError as e:
                db.session.rollback()
                await message.answer("Произошла ошибка при привязке аккаунта. Попробуйте позже.")
                logger.error(f"IntegrityError при привязке telegram_user_id={telegram_user_id} к дезинсектору id={disinsector.id}: {e}")
                return

            welcome_text = f"Добро пожаловать, {disinsector.name}! Вы успешно зарегистрировались и можете принимать заявки."
            send_telegram_message(token, telegram_user_id, welcome_text)

            await state.update_data(disinsector_id=disinsector.id)

            await message.answer("Добрый день! Нажмите 'Ок', чтобы принять заявку и начать опрос.",
                                 reply_markup=inl_kb_accept_order)
            await state.set_state(OrderForm.accept_order)

        except Exception as e:
            logger.error(f"Произошла ошибка при обработке команды /start: {e}")
            await message.answer("Произошла ошибка при обработке команды /start. Попробуйте позже.")



    # Обработчики для работы с заявкой
    @dp.callback_query(F.data == 'accept_order_yes', StateFilter(OrderForm.accept))
    async def accept_order(callback: types.CallbackQuery, state: FSMContext):
        user_data = await state.get_data()
        disinsector_id = user_data['disinsector_id']  # Используем disinsector_id из состояния

        # Получаем первую заявку с статусом 'Новая'
        order = db.session.query(Order).filter_by(disinsector_id=disinsector_id, order_status='Новая').first()

        if order:
            order.order_status = 'В процессе'
            db.session.commit()
            await callback.answer("Заявка принята.")
            await callback.message.answer("Вы приняли заявку. Укажите тип химиката для обработки.", reply_markup=inl_kb_chemical_type)
            await state.set_state(OrderForm.chemical_type)

            # Передаем заявку в общую функцию назначения и уведомления, передав объект bot
            assign_and_notify_disinsector(bot, order)  # Передаем bot в функцию

        else:
            await callback.answer("Ошибка, заявка не найдена.")


    @dp.callback_query(StateFilter(OrderForm.chemical_type))
    async def process_chemical_type(callback: types.CallbackQuery, state: FSMContext):
        await state.update_data(chemical_type=callback.data)
        await callback.message.answer("Укажите площадь помещения (в кв.м).")
        await state.set_state(OrderForm.area)

    @dp.message(StateFilter(OrderForm.area))
    async def process_area(message: types.Message, state: FSMContext):
        await state.update_data(area=message.text)
        await message.answer("Укажите тип яда.", reply_markup=inl_kb_poison_type)
        await state.set_state(OrderForm.poison_type)

    @dp.callback_query(StateFilter(OrderForm.poison_type))
    async def process_poison_type(callback: types.CallbackQuery, state: FSMContext):
        await state.update_data(poison_type=callback.data)
        await callback.message.answer("Укажите тип насекомых.", reply_markup=inl_kb_insect_type)
        await state.set_state(OrderForm.insect_type)

    @dp.callback_query(StateFilter(OrderForm.insect_type))
    async def process_insect_type(callback: types.CallbackQuery, state: FSMContext):
        await state.update_data(insect_type=callback.data)
        await callback.message.answer("Укажите примерную стоимость.")
        await state.set_state(OrderForm.estimated_cost)

    @dp.message(StateFilter(OrderForm.estimated_cost))
    async def process_estimated_cost(message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        order = db.session.query(Order).filter_by(disinsector_id=user_data['disinsector_id'], order_status='Новая').first()

        if order:
            order.chemical_type = user_data['chemical_type']
            order.area = user_data['area']
            order.poison_type = user_data['poison_type']
            order.insect_type = user_data['insect_type']
            order.estimated_cost = user_data['estimated_cost']
            order.order_status = 'В процессе'
            db.session.commit()
            await message.answer("Данные заявки обновлены и заявка переведена в статус 'В процессе'.")
        else:
            await message.answer("Ошибка при обновлении заявки.")
        await state.clear()

    await dp.start_polling(bot)

# Функция назначения дезинсектора и уведомления
async def assign_and_notify_disinsector(order):
    """
    Назначает дезинсектора для заявки и отправляет ему уведомление.
    """
    try:
        # Запрос доступных дезинсекторов
        available_disinsectors = Disinsector.query.filter(
            Disinsector.token.isnot(None),
            Disinsector.telegram_user_id.isnot(None),
            Disinsector.load < Disinsector.max_load
        ).order_by(Disinsector.last_assigned).all()

        if not available_disinsectors:
            logger.warning(f"Заявка {order.id}: Нет доступных дезинсекторов для назначения.")
            return None

        # Назначение дезинсектора
        disinsector = available_disinsectors[0]
        order.disinsector_id = disinsector.id  # Присваиваем disinsector_id заказу
        disinsector.last_assigned = datetime.utcnow()
        disinsector.load += 1
        db.session.commit()

        # Создаем бота с токеном дезинсектора и отправляем уведомление
        bot_disinsector = Bot(token=disinsector.token)
        await notify_new_order(bot_disinsector, disinsector, order)

        return disinsector

    except Exception as e:
        logger.error(f"Ошибка при назначении дезинсектора для заявки {order.id}: {e}")
        db.session.rollback()
        return None

# Функция уведомления дезинсектора
async def notify_new_order(bot, disinsector, order):
    """
    Отправляет уведомление дезинсектору о новой заявке с кнопкой "Ок" для принятия.
    """
    try:
        buttons = inl_kb_accept_order

        message = (
            f"🔔 Новая заявка №{order.id}.\n"
            f"Имя: {order.client.name}\n"
            f"Адрес: {order.client.address}\n"
            f"Телефон: {order.client.phone}\n"
            f"Объект: {order.object_type}\n"

        )

        # Отправляем сообщение с кнопками
        await bot.send_message(disinsector.telegram_user_id, message, reply_markup=buttons)
        logger.info(f"Уведомление отправлено дезинсектору {disinsector.name}")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления дезинсектору {disinsector.name}: {e}")
        # Дополнительная диагностика ошибок
        if "chat not found" in str(e):
            logger.error(f"Не удалось отправить сообщение дезинсектору с ID {disinsector.telegram_user_id}. Возможно, он не начал чат с ботом.")
        else:
            logger.error(f"Неизвестная ошибка при отправке сообщения: {e}")



# Основная функция для запуска всех ботов
async def disinsector_bot_main():
    app = create_app()
    with app.app_context():
        disinsectors = Disinsector.query.filter(Disinsector.token.isnot(None)).all()
        tasks = [
            start_disinsector_bot(disinsector.token, disinsector.id)
            for disinsector in disinsectors
        ]
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(disinsector_bot_main())
