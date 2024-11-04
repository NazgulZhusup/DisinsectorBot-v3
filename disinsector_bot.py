import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from app.model import Disinsector, Order
from database import db
from config import Config
from app.keyboards import *
from app import create_app

# Настройка логирования
logger = logging.getLogger('disinsector_bot')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('disinsector_bot.log')
stream_handler = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Инициализация Flask-приложения и контекста
app = create_app()
app_context = app.app_context()
app_context.push()

logger.info(f"Используемая база данных: {Config.SQLALCHEMY_DATABASE_URI}")

async def start_disinsector_bot(token, disinsector_id):
    storage = MemoryStorage()
    try:
        bot = Bot(token=token)
        await bot.get_me()  # Проверка токена
    except Exception as e:
        logger.error(f"Неверный токен для дезинсектора id={disinsector_id}: {e}")
        return

    dp = Dispatcher(storage=storage)

    # Обработчик команды /start
    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        try:
            telegram_user_id = message.from_user.id
            logger.info(f"Получен запрос на регистрацию от telegram_user_id={telegram_user_id}")

            # Работаем с db.session внутри контекста приложения Flask
            disinsector = db.session.query(Disinsector).filter_by(id=disinsector_id).first()
            if not disinsector:
                await message.answer("Ошибка авторизации. Некорректный токен.")
                logger.error(f"Дезинсектор с id {disinsector_id} не найден.")
                return

            logger.info(f"Дезинсектор {disinsector.name} ({disinsector.id}) найден. Проверка telegram_user_id={telegram_user_id}")

            # Проверяем, привязан ли уже этот telegram_user_id к другому дезинсектору
            existing = db.session.query(Disinsector).filter_by(telegram_user_id=telegram_user_id).first()
            if existing and existing.id != disinsector.id:
                await message.answer("Этот Telegram аккаунт уже привязан к другому дезинсектору.")
                logger.warning(f"Пользователь с telegram_user_id={telegram_user_id} пытается привязаться к дезинсектору id={disinsector.id}, но уже привязан к id={existing.id}")
                return

            # Привязка telegram_user_id к текущему дезинсектору
            disinsector.telegram_user_id = telegram_user_id
            try:
                db.session.commit()
                logger.info(f"Присвоен telegram_user_id={telegram_user_id} дезинсектору id={disinsector.id}")
            except IntegrityError:
                db.session.rollback()
                await message.answer("Произошла ошибка при привязке аккаунта. Попробуйте позже.")
                logger.error(f"IntegrityError при привязке telegram_user_id={telegram_user_id} к дезинсектору id={disinsector.id}")
                return

            await state.update_data(disinsector_id=disinsector.id)
            await message.answer(
                f"Добро пожаловать, {disinsector.name}! Вы успешно зарегистрировались. Теперь вы можете принимать заявки."
            )
            logger.info(f"Дезинсектор {disinsector.name} ({disinsector.id}) зарегистрирован с telegram_user_id {telegram_user_id}")
        except Exception as e:
            logger.error(f"Ошибка в обработчике /start: {e}")
            await message.answer("Произошла ошибка при регистрации.")

    @dp.callback_query(F.data.startswith('accept_order_'))
    async def process_accept_order(callback_query: types.CallbackQuery, state: FSMContext):
        order_id = int(callback_query.data.split('_')[-1])
        user_data = await state.get_data()
        disinsector_id = user_data.get('disinsector_id')

        try:
            order = db.session.query(Order).filter_by(id=order_id).first()
            if order:
                if order.disinsector_id is None:
                    order.disinsector_id = disinsector_id
                    order.order_status = 'В процессе'
                    db.session.commit()
                    await callback_query.answer("Вы приняли заявку.")
                    await callback_query.message.answer(f"Вы приняли заявку №{order_id}.")
                    logger.info(f"Заявка {order_id} принята дезинсектором {disinsector_id}")
                else:
                    await callback_query.answer("Эта заявка уже была принята другим дезинсектором.", show_alert=True)
            else:
                await callback_query.answer("Заявка не найдена.", show_alert=True)
                logger.error(f"Заявка {order_id} не найдена.")
        except Exception as e:
            logger.error(f"Ошибка в обработчике принятия заявки: {e}")
            await callback_query.answer("Произошла ошибка при принятии заявки.", show_alert=True)

    @dp.callback_query(F.data.startswith('decline_order_'))
    async def process_decline_order(callback_query: types.CallbackQuery, state: FSMContext):
        order_id = int(callback_query.data.split('_')[-1])

        try:
            order = db.session.query(Order).filter_by(id=order_id).first()
            if order:
                order.order_status = 'Отклонена'
                db.session.commit()
                await callback_query.answer("Вы отклонили заявку.")
                await callback_query.message.answer(f"Вы отклонили заявку №{order_id}.")
                logger.info(f"Заявка {order_id} отклонена дезинсектором.")
            else:
                await callback_query.answer("Заявка не найдена.", show_alert=True)
                logger.error(f"Заявка {order_id} не найдена.")
        except Exception as e:
            logger.error(f"Ошибка в обработчике отклонения заявки: {e}")
            await callback_query.answer("Произошла ошибка при отклонении заявки.", show_alert=True)

    @dp.message(F.text == 'Мои заявки')
    async def show_orders(message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        disinsector_id = user_data.get('disinsector_id')

        try:
            orders = db.session.query(Order).filter_by(disinsector_id=disinsector_id).options(joinedload(Order.client)).all()
            if orders:
                for order in orders:
                    order_info = (
                        f"<b>Заявка №{order.id}</b>\n"
                        f"Клиент: {order.client.name}\n"
                        f"Телефон: {order.client.phone}\n"
                        f"Адрес: {order.client.address}\n"
                        f"Статус: {order.order_status}"
                    )
                    await message.answer(order_info, parse_mode='HTML')
            else:
                await message.answer("У вас нет активных заявок.")
        except Exception as e:
            logger.error(f"Ошибка в обработчике команды 'Мои заявки': {e}")
            await message.answer("Произошла ошибка при получении ваших заявок.")

    await dp.start_polling(bot)

async def main():
    try:
        # Получаем всех дезинсекторов, которые имеют токен бота и привязаны к Telegram User ID
        disinsectors = db.session.query(Disinsector).filter(
            Disinsector.token.isnot(None),
            Disinsector.telegram_user_id.isnot(None)
        ).all()
        if not disinsectors:
            logger.error("Нет дезинсекторов для запуска ботов.")
            return

        tasks = []
        for disinsector in disinsectors:
            token = disinsector.token
            disinsector_id = disinsector.id
            tasks.append(start_disinsector_bot(token, disinsector_id))

        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == '__main__':
    asyncio.run(main())
