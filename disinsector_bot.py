import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from app.model import Disinsector, Order
from database import db
from config import Config
from app.utils import send_telegram_message
from app import create_app

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
    confirm = State()
    chemical_type = State()
    area = State()
    poison_type = State()
    insect_type = State()
    estimated_cost = State()


# Асинхронная функция запуска бота дезинсектора
async def start_disinsector_bot(token, disinsector_id):
    storage = MemoryStorage()
    bot = Bot(token=token)
    dp = Dispatcher(bot=bot, storage=storage)

    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        disinsector = db.session.get(Disinsector, disinsector_id)
        if disinsector:
            await message.answer(f"Добро пожаловать, {disinsector.name}! Вы можете просматривать и управлять заявками.")
        else:
            await message.answer("Ошибка авторизации.")

    @dp.message(F.text == 'Принять заявку')
    async def confirm_order(message: types.Message, state: FSMContext):
        order = db.session.query(Order).filter_by(disinsector_id=disinsector_id, order_status='Новая').first()
        if order:
            await message.answer("Вы приняли заявку. Укажите тип химиката.")
            await state.set_state(OrderForm.chemical_type)
        else:
            await message.answer("У вас нет новых заявок.")

    @dp.message(StateFilter(OrderForm.chemical_type))
    async def process_chemical_type(message: types.Message, state: FSMContext):
        await state.update_data(chemical_type=message.text)
        await message.answer("Укажите площадь помещения (в кв.м).")
        await state.set_state(OrderForm.area)

    @dp.message(StateFilter(OrderForm.area))
    async def process_area(message: types.Message, state: FSMContext):
        await state.update_data(area=message.text)
        await message.answer("Укажите тип яда.")
        await state.set_state(OrderForm.poison_type)

    @dp.message(StateFilter(OrderForm.poison_type))
    async def process_poison_type(message: types.Message, state: FSMContext):
        await state.update_data(poison_type=message.text)
        await message.answer("Укажите тип насекомых.")
        await state.set_state(OrderForm.insect_type)

    @dp.message(StateFilter(OrderForm.insect_type))
    async def process_insect_type(message: types.Message, state: FSMContext):
        await state.update_data(insect_type=message.text)
        await message.answer("Укажите примерную стоимость.")
        await state.set_state(OrderForm.estimated_cost)

    @dp.message(StateFilter(OrderForm.estimated_cost))
    async def process_estimated_cost(message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        order = db.session.query(Order).filter_by(disinsector_id=disinsector_id, order_status='Новая').first()
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

    await dp.start_polling(bot)


# Основная функция для запуска всех ботов
async def disinsector_bot_main():
    app = create_app()
    with app.app_context():  # Используем синхронный with для app_context
        disinsectors = Disinsector.query.filter(Disinsector.token.isnot(None)).all()
        tasks = [
            start_disinsector_bot(disinsector.token, disinsector.id)
            for disinsector in disinsectors
        ]
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(disinsector_bot_main())
