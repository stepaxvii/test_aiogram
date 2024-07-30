"""Основной файл тестового задания."""
import aiohttp
import asyncio
import logging
import sys
import time
from os import getenv
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Из окружения извлекаем необходимые токены и ссылки
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
OWM_API_KEY = getenv('OWM_API_KEY')

# Создаём экземпляр класса Dispatcher для обработки обновлений
dp = Dispatcher()

# Настраиваем базы данных
DATABASE_URL = "sqlite:///d:/Dev/testing_aio/users.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


class User(Base):
    """Модель пользователя."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)


# Создаём таблицы
Base.metadata.create_all(engine)


class UserDataForm(StatesGroup):
    """Определение состояния FMS при старте при запуске бота."""

    name = State()
    age = State()


class WeatherForm(StatesGroup):
    """Определение состояния FMS при запросе команды /weather."""

    city = State()


@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    """Обработка команды start и создание inline клавиатуры."""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Вариант 1', callback_data='sel 1')],
            [InlineKeyboardButton(text='Вариант 2', callback_data='sel 2')]
        ]
    )
    user_name = message.from_user.full_name if message.from_user else "User"
    await message.answer(
        f'Привет, <b>{user_name}</b>!\n'
        'Выбери свой вариант:',
        parse_mode_key='HTML',
        reply_markup=keyboard
        )


@dp.callback_query()
async def callback_process(
    callback_query: types.CallbackQuery,
    state: FSMContext
):
    """Обработка callback-оф и переход к тестированию FMS."""

    selected_option = callback_query.data
    if selected_option == 'sel 1':
        await callback_query.message.answer(
            'Вы выбрали вариант 1'
        )
    elif selected_option == 'sel 2':
        await callback_query.message.answer(
            'Вы выбрали вариант 2.'
            '\nПереходим к тестированию FMS'
        )
        time.sleep(2)
        await state.set_state(UserDataForm.name)
        await callback_query.message.answer(
            'Как тебя зовут?'
        )


@dp.message(StateFilter(UserDataForm.name))
async def process_name(
    message: types.Message,
    state: FSMContext
):
    """Обработчик состояния UserDataForm.name."""

    await state.update_data(name=message.text)
    await state.set_state(UserDataForm.age)
    await message.answer('Сколько тебе лет?')


@dp.message(StateFilter(UserDataForm.age))
async def process_age_and_data_output(
    message: types.Message,
    state: FSMContext
):
    """Обработчик состояния UserDataForm.age и вывод данных."""

    await state.update_data(age=message.text)

    user_data = await state.get_data()
    name, age = user_data.get('name'), int(user_data.get('age'))
    session = Session()
    new_user = User(user_id=message.from_user.id, name=name, age=age)
    session.add(new_user)
    session.commit()
    session.close()
    await message.answer(
        f'Круто, {name}! {age} лучший возраст!\n'
        'Отправив команду /users, можно получить список пользователей из БД)'
    )
    await state.clear()


@dp.message(Command('users'))
async def command_users_handler(message: types.Message):
    """Обработка команды /users для вывода всех пользователей."""
    session = Session()
    users = session.query(User).all()
    session.close()

    if users:
        user_list = "\n".join(
            [
                f'ID: {user.user_id}, '
                f'Имя: {user.name}, '
                f'Возраст: {user.age}' for user in users
            ]
        )
        await message.answer(f'Список пользователей:\n{user_list}')
    else:
        await message.answer('Пользователи не найдены в базе данных.')


@dp.message(F.content_type == types.ContentType.PHOTO)
async def process_image(message: types.Message):
    """Возвращение юзеру размеров, отправленного им изображения."""

    photo = message.photo[-1]
    width = photo.width
    height = photo.height
    await message.answer(
        f'Размер вашего изображения: {width} x {height} пикселей.'
    )


@dp.message(Command('help'))
async def command_help_handler(message: types.Message):
    """Обработка команды help."""

    await message.answer(
        'Обработали запрос команды /help.'
    )


@dp.message(Command('echo'))
async def command_echo_handler(message: types.Message):
    """Обработка команды echo."""

    await message.answer(
        'Реализовал обработчик неизвестных запросов методом echo.'
        'Если бот не знает, что делать с сообщением - просто вернёт такое же.'
    )


@dp.message(Command('weather'))
async def command_weather_handler(
    message: types.Message,
    state: FSMContext
):
    """Обработка команды weather."""

    await state.set_state(WeatherForm.city)
    await message.answer(
        'Погоду какого города ты хочешь узнать?'
    )


@dp.message(StateFilter(WeatherForm.city))
async def response_weather(message: types.Message, state: FSMContext):
    """Получаем погоду по запрошенному городу, либо запрашиваем повторно."""
    city = message.text
    async with aiohttp.ClientSession() as session:
        url = (
            'http://api.openweathermap.org'
            f'/data/2.5/weather?q={city}&appid={OWM_API_KEY}&units=metric'
        )
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                temp = data['main']['temp']
                humidity = data['main']['humidity']
                await message.answer(
                    f'Погода в городе {city}:\n'
                    f'Температура - {int(temp)}°C, влажность - {humidity}%'
                )
                await state.clear()
        except aiohttp.ClientError:
            await message.answer(
                'Ошибка на стороне сервера. Повтори попытку позже'
                )
            await state.clear()
        except Exception:
            await message.answer(
                'Не удалось получить данные о погоде.\n'
                'Возможно ошибка в названии города'
            )


@dp.message()
async def echo_handler(message: types.Message):
    """Возвращение юзеру его же сообщения."""

    try:
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        await message.answer("Хитро!")


async def main():
    # Создаём экземпляр класса Bot
    bot = Bot(
        token=TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Запускаем обработку обновлений
    await dp.start_polling(bot)


if __name__ == '__main__':
    # Фиксируем логи в терминале
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
    )
    asyncio.run(main())
