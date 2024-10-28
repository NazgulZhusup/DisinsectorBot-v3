import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from app.model import Disinsector, Order
from app import db, create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("disinsector_bot.log"),
        logging.StreamHandler()
    ]
)

# Создаем приложение и контекст приложения
app = create_app()
app_context = app.app_context()
app_context.push()

async def run_blocking_db_operation(operation, *args, **kwargs):
    """Запускает блокирующую операцию с базой данных в отдельном потоке, внутри контекста приложения."""
    loop = asyncio.get_event_loop()

    def run_operation():
        with app.app_context():
            return operation(*args, **kwargs)

    return await loop.run_in_executor(None, run_operation)


async def start_disinsector_bot(token):
    logging.info(f"Starting disinsector bot with token: {token}")
    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(bot=bot, storage=storage)

    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        def fetch_disinsector():
            return Disinsector.query.filter_by(token=token).first()

        disinsector = await run_blocking_db_operation(fetch_disinsector)
        if disinsector:
            user_id = message.from_user.id
            disinsector.user_id = user_id  # Обновляем user_id дезинсектора

            # Сохраняем изменения в базе данных
            def commit_changes():
                db.session.commit()

            await run_blocking_db_operation(commit_changes)
            await state.update_data(disinsector_id=disinsector.id)
            await message.answer(f"Добро пожаловать, {disinsector.name}!")
            logging.info(f"Disinsector {disinsector.name} ({disinsector.id}) registered with user_id {user_id}")
        else:
            await message.answer("Ошибка авторизации. Некорректный токен.")
            logging.error(f"Disinsector with token {token} not found.")

    # Здесь можно добавить обработчики для получения новых заявок и взаимодействия с дезинсектором

    await dp.start_polling(bot)


async def main():
    def get_disinsector_tokens():
        """Получает все токены дезинсекторов из базы данных."""
        with app.app_context():
            return [disinsector.token for disinsector in Disinsector.query.all()]

    tokens = await run_blocking_db_operation(get_disinsector_tokens)
    if not tokens:
        logging.error("Нет токенов дезинсекторов для запуска ботов.")
        return
    tasks = [start_disinsector_bot(token) for token in tokens]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
