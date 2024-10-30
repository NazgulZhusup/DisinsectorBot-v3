# disinsector_bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.model import Disinsector, Order, Client
from app import create_app
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("disinsector_bot.log"),
        logging.StreamHandler()
    ]
)

# Инициализация Flask-приложения и контекста
app = create_app()
app_context = app.app_context()
app_context.push()

# Определение абсолютного пути к базе данных
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'app/entoforce_database.db')  # Убедитесь, что имя файла совпадает
db_uri = f'sqlite:///{db_path}'
logging.info(f"Используемая база данных: {db_uri}")

# Создание SQLAlchemy engine и session
engine = create_engine(db_uri)
Session = scoped_session(sessionmaker(bind=engine))

async def start_disinsector_bot(token, disinsector_id):
    storage = MemoryStorage()
    bot = Bot(token=token)
    dp = Dispatcher(storage=storage)

    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        session = Session()
        try:
            disinsector = session.query(Disinsector).filter_by(id=disinsector_id).first()
            if disinsector:
                user_id = message.from_user.id
                disinsector.user_id = user_id
                session.commit()
                await state.update_data(disinsector_id=disinsector.id)
                await message.answer(f"Добро пожаловать, {disinsector.name}! Вы успешно зарегистрировались. Ваш user_id {user_id}.  Теперь вы можете принимать заявки.")
                logging.info(f"Дезинсектор {disinsector.name} ({disinsector.id}) зарегистрирован с user_id {user_id}")
            else:
                await message.answer("Ошибка авторизации. Некорректный токен.")
                logging.error(f"Дезинсектор с id {disinsector_id} не найден.")
        except Exception as e:
            logging.error(f"Ошибка в обработчике /start: {e}")
            await message.answer("Произошла ошибка при регистрации.")
        finally:
            session.close()

    @dp.callback_query(F.data.startswith('accept_order_'))
    async def process_accept_order(callback_query: types.CallbackQuery, state: FSMContext):
        order_id = int(callback_query.data.split('_')[-1])
        user_data = await state.get_data()
        disinsector_id = user_data.get('disinsector_id')

        session = Session()
        try:
            order = session.query(Order).get(order_id)
            if order:
                if order.disinsector_id is None:
                    order.disinsector_id = disinsector_id
                    order.order_status = 'В процессе'
                    session.commit()
                    await callback_query.answer("Вы приняли заявку.")
                    await callback_query.message.answer(f"Вы приняли заявку №{order_id}.")
                    logging.info(f"Заявка {order_id} принята дезинсектором {disinsector_id}")
                else:
                    await callback_query.answer("Эта заявка уже была принята другим дезинсектором.", show_alert=True)
            else:
                await callback_query.answer("Заявка не найдена.", show_alert=True)
                logging.error(f"Заявка {order_id} не найдена.")
        except Exception as e:
            logging.error(f"Ошибка в обработчике принятия заявки: {e}")
            await callback_query.answer("Произошла ошибка при принятии заявки.", show_alert=True)
        finally:
            session.close()

    @dp.callback_query(F.data.startswith('decline_order_'))
    async def process_decline_order(callback_query: types.CallbackQuery, state: FSMContext):
        order_id = int(callback_query.data.split('_')[-1])

        session = Session()
        try:
            order = session.query(Order).get(order_id)
            if order:
                order.order_status = 'Отклонена'
                session.commit()
                await callback_query.answer("Вы отклонили заявку.")
                await callback_query.message.answer(f"Вы отклонили заявку №{order_id}.")
                logging.info(f"Заявка {order_id} отклонена дезинсектором.")
            else:
                await callback_query.answer("Заявка не найдена.", show_alert=True)
                logging.error(f"Заявка {order_id} не найдена.")
        except Exception as e:
            logging.error(f"Ошибка в обработчике отклонения заявки: {e}")
            await callback_query.answer("Произошла ошибка при отклонении заявки.", show_alert=True)
        finally:
            session.close()

    @dp.message(F.text == 'Мои заявки')
    async def show_orders(message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        disinsector_id = user_data.get('disinsector_id')

        session = Session()
        try:
            orders = session.query(Order).filter_by(disinsector_id=disinsector_id).all()
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
            logging.error(f"Ошибка в обработчике команды 'Мои заявки': {e}")
            await message.answer("Произошла ошибка при получении ваших заявок.")
        finally:
            session.close()

    await dp.start_polling(bot)

async def main():
    session = Session()
    try:
        disinsectors = session.query(Disinsector).all()
        if not disinsectors:
            logging.error("Нет дезинсекторов для запуска ботов.")
            return

        tasks = []
        for disinsector in disinsectors:
            token = disinsector.token
            disinsector_id = disinsector.id
            if token:
                tasks.append(start_disinsector_bot(token, disinsector_id))
            else:
                logging.warning(f"Дезинсектор {disinsector.name} не имеет токена бота.")

        await asyncio.gather(*tasks)
    except Exception as e:
        logging.error(f"Error in main: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    asyncio.run(main())
