import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
import keyboards as kb
from config import TOKEN  # Убедитесь, что TOKEN определен в config.py

client_token = TOKEN
bot = Bot(token=client_token)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("client_bot.log"),
        logging.StreamHandler()
    ]
)


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
        reply_markup=kb.inl_kb_greetings
    )
    await state.set_state(ClientForm.waiting_for_start)


@dp.callback_query(F.data == 'start', StateFilter(ClientForm.waiting_for_start))
async def process_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Расскажите, пожалуйста, подробнее об объекте. У вас:",
        reply_markup=kb.inl_kb_object_type
    )
    await state.set_state(ClientForm.object_type)


@dp.callback_query(F.data.startswith('object_'), StateFilter(ClientForm.object_type))
async def process_object(callback: types.CallbackQuery, state: FSMContext):
    object_selected = callback.data.split('_', 1)[1]
    await state.update_data(object_type=object_selected)
    await callback.answer()
    await callback.message.answer(
        "Сколько насекомых вы обнаружили?",
        reply_markup=kb.inl_kb_insect_quantity
    )
    await state.set_state(ClientForm.insect_quantity)


@dp.callback_query(F.data.startswith('quantity_'), StateFilter(ClientForm.insect_quantity))
async def process_insect_quantity(callback: types.CallbackQuery, state: FSMContext):
    quantity_selected = callback.data.split('_', 1)[1]
    await state.update_data(insect_quantity=quantity_selected)
    await callback.answer()
    await callback.message.answer(
        "Есть ли у вас опыт дезинсекции?",
        reply_markup=kb.inl_kb_experience
    )
    await state.set_state(ClientForm.disinsect_experience)


@dp.callback_query(F.data.startswith('experience_'), StateFilter(ClientForm.disinsect_experience))
async def process_disinsect_experience(callback: types.CallbackQuery, state: FSMContext):
    experience_selected = callback.data.split('_', 1)[1]
    await state.update_data(disinsect_experience=experience_selected)
    await callback.answer()
    await callback.message.answer(
        "Пожалуйста, отправьте ваш номер телефона:",
        reply_markup=kb.kb_contact
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

        user_data = await state.get_data()

        payload = {
            'client_name': user_data['name'],
            'object_type': user_data['object_type'],
            'insect_quantity': user_data['insect_quantity'],
            'disinsect_experience': user_data['disinsect_experience'],
            'phone_number': user_data['phone'],
            'address': user_data['address'],
        }

        logging.info(f"Отправка данных на сервер: {payload}")

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post('http://127.0.0.1:5000/api/create_order', json=payload, headers=headers) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        await message.answer(
                            f"Спасибо, {user_data['name']}! Ваша заявка принята. Мы скоро свяжемся с вами."
                        )
                        await state.clear()
                    else:
                        logging.error(f"Ошибка при отправке данных на сервер: {response.status}, Ответ сервера: {response_text}")
                        await message.answer("Произошла ошибка при сохранении данных заявки. Пожалуйста, попробуйте снова.")
            except aiohttp.ClientError as e:
                logging.error(f"Ошибка сети при отправке данных: {e}")
                await message.answer("Сетевая ошибка при сохранении данных заявки. Пожалуйста, попробуйте снова.")
    except Exception as e:
        logging.error(f"Ошибка при обработке адреса: {e}")
        await message.answer("Произошла ошибка при сохранении данных заявки. Пожалуйста, попробуйте снова.")


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
