import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from keyboards import *
from config import Config
from app import create_app
from app.model import Client, Order, Disinsector
from database import db
from disinsector_bot import assign_and_notify_disinsector

# Настройка логирования
logger = logging.getLogger('client_bot')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('client_bot.log')
stream_handler = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Инициализация бота и диспетчера
client_token = Config.CLIENT_BOT_TOKEN

if not client_token:
    logger.error("CLIENT_BOT_TOKEN не установлен в конфигурации.")
    raise ValueError("CLIENT_BOT_TOKEN не установлен в конфигурации.")
else:
    logger.info("CLIENT_BOT_TOKEN успешно загружен.")

bot_client = Bot(token=client_token)
storage = MemoryStorage()
dp = Dispatcher(bot=bot_client, storage=storage)

# FSM States
class ClientForm(StatesGroup):
    name = State()
    waiting_for_start = State()
    object_type = State()
    insect_quantity = State()
    disinsect_experience = State()
    phone = State()
    address = State()

@dp.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    await message.answer("Добрый день! Как к вам можно обращаться?")
    await state.set_state(ClientForm.name)

@dp.message(ClientForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        f"{message.text}, ответьте, пожалуйста, на несколько вопросов, чтобы мы могли просчитать стоимость дезинсекции.",
        reply_markup=inl_kb_greetings
    )
    await state.set_state(ClientForm.waiting_for_start)

@dp.callback_query(F.data == 'start', StateFilter(ClientForm.waiting_for_start))
async def process_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Расскажите, пожалуйста, подробнее об объекте. У вас:",
        reply_markup=inl_kb_object_type
    )
    await state.set_state(ClientForm.object_type)

@dp.callback_query(F.data.startswith('object_'), StateFilter(ClientForm.object_type))
async def process_object(callback: types.CallbackQuery, state: FSMContext):
    object_selected = callback.data.split('_', 1)[1]
    await state.update_data(object_type=object_selected)
    await callback.answer()
    await callback.message.answer(
        "Сколько насекомых вы обнаружили?",
        reply_markup=inl_kb_insect_quantity
    )
    await state.set_state(ClientForm.insect_quantity)

@dp.callback_query(F.data.startswith('quantity_'), StateFilter(ClientForm.insect_quantity))
async def process_insect_quantity(callback: types.CallbackQuery, state: FSMContext):
    quantity_selected = callback.data.split('_', 1)[1]
    await state.update_data(insect_quantity=quantity_selected)
    await callback.answer()
    await callback.message.answer(
        "Есть ли у вас опыт дезинсекции?",
        reply_markup=inl_kb_experience
    )
    await state.set_state(ClientForm.disinsect_experience)

@dp.callback_query(F.data.startswith('experience_'), StateFilter(ClientForm.disinsect_experience))
async def process_disinsect_experience(callback: types.CallbackQuery, state: FSMContext):
    experience_selected = callback.data.split('_', 1)[1]
    await state.update_data(disinsect_experience=experience_selected)
    await callback.answer()
    await callback.message.answer(
        "Пожалуйста, отправьте ваш номер телефона:",
        reply_markup=kb_contact
    )
    await state.set_state(ClientForm.phone)

@dp.message(ClientForm.phone, F.content_type == types.ContentType.CONTACT)
async def process_phone_contact(message: types.Message, state: FSMContext):
    phone = re.sub(r'\D', '', message.contact.phone_number)
    await state.update_data(phone=phone)
    await message.answer("Пожалуйста, введите ваш домашний адрес:")
    await state.set_state(ClientForm.address)

@dp.message(ClientForm.phone, F.content_type == types.ContentType.TEXT)
async def process_phone_text(message: types.Message, state: FSMContext):
    phone = re.sub(r'\D', '', message.text)
    if not re.fullmatch(r'\d{10,15}', phone):
        await message.answer("Пожалуйста, введите корректный номер телефона.")
        return
    await state.update_data(phone=phone)
    await message.answer("Пожалуйста, введите ваш домашний адрес:")
    await state.set_state(ClientForm.address)

@dp.message(ClientForm.address)
async def process_address(message: types.Message, state: FSMContext):
    try:
        address = message.text.strip()
        if len(address) < 5:
            await message.answer("Пожалуйста, введите ваш домашний адрес.")
            return
        await state.update_data(address=address)

        # Получаем все данные из состояния
        user_data = await state.get_data()

        # Сохраняем клиента в базе данных
        client = Client.query.filter_by(phone=user_data['phone']).first()
        if not client:
            client = Client(name=user_data['name'], phone=user_data['phone'], address=user_data['address'])
            db.session.add(client)
            db.session.commit()

        # Создаем новую заявку
        disinsect_experience = user_data['disinsect_experience'] == 'yes'
        new_order = Order(
            client_id=client.id,
            object_type=user_data['object_type'],
            insect_quantity=user_data['insect_quantity'],
            disinsect_experience=disinsect_experience,
            order_status='Новая'
        )
        db.session.add(new_order)
        db.session.commit()

        logger.info(f"Заявка {new_order.id} успешно создана.")

        # Назначаем дезинсектора и отправляем уведомление

        assigned_disinsector = await assign_and_notify_disinsector(new_order)

        if assigned_disinsector:
            new_order.disinsector_id = assigned_disinsector.id
            db.session.commit()  # Сохраняем обновленный заказ с disinsector_id
            logger.info(f"Заявка {new_order.id} назначена дезинсектору {assigned_disinsector.name}")
            await message.answer("Спасибо! Ваша заявка принята и назначена дезинсектору. Мы скоро свяжемся с вами.")
        else:
            logger.warning("Нет доступных дезинсекторов для назначения заявки.")
            await message.answer("Ваша заявка принята, но пока нет доступного дезинсектора. Мы свяжемся с вами позже.")


        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при создании заявки: {e}")
        await message.answer("Произошла ошибка при обработке заявки. Пожалуйста, попробуйте снова.")


async def main():
    app = create_app()
    with app.app_context():  # Используем обычный синхронный контекст
        await dp.start_polling(bot_client)

if __name__ == '__main__':
    asyncio.run(main())