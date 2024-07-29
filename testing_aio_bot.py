"""Основной файл тестового задания."""

import asyncio
import logging
import sys
from os import getenv

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


load_dotenv()


# Из окружения извлекаем необходимые токены и ссылки
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')

# Создаём экземпляр класса Dispatcher для обработки обновлений
dp = Dispatcher()


class UserDataForm(StatesGroup):
    """Определение состояний FMS при старте при запуске бота."""

    name = State()
    age = State()


class ImageUploadForm(StatesGroup):
    """Определение состояний FMS при получении изображения."""

    image = State()


@dp.message(CommandStart())
async def command_start_handler(
    message: types.Message
):
    """Обработка команды start и создание inline клавиатуры."""

    keybord = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text='Вариант 1',
                callback_data='вариант1'
            )],
            [InlineKeyboardButton(
                text='Вариант 2',
                callback_data='вариант2'
            )]
        ]
    )
    user_name = message.from_user.full_name if message.from_user else "User"
    await message.answer(
        f'Hello, {user_name}! \n'
        'Выбери свой вариант:',
        reply_markup=keybord
        )


@dp.callback_query()
async def callback_process(
    callback_query: types.CallbackQuery,
    state: FSMContext
):
    """Обработка callback-оф и переход к тестированию FMS."""

    selected_option = callback_query.data

    if selected_option == 'вариант1':
        await callback_query.message.edit_text(
            'Вы выбрали вариант 1.'
        )
        await state.set_state(UserDataForm.name)
        # Начало заполнения формы
        await callback_query.message.answer('Как тебя зовут?')

    elif selected_option == 'вариант2':
        await callback_query.message.edit_text(
            'Вы выбрали вариант 2.'
        )
        await state.set_state(UserDataForm.name)
        # Начало заполнения формы
        await callback_query.message.answer('Как тебя зовут?')
    await callback_query.answer()


@dp.message(StateFilter(UserDataForm.name))
async def process_name(
    message: types.Message,
    state: FSMContext
):
    """Обработчик контекстного состояния name."""

    # Сохраняем имя в контексте состояния
    await state.update_data(name=message.text)
    # Переходим к следующему состоянию
    await state.set_state(UserDataForm.age)
    await message.answer('Сколько тебе лет?')


@dp.message(StateFilter(UserDataForm.age))
async def process_age(
    message: types.Message,
    state: FSMContext
):
    # Сохраняем возраст в контексте состояния
    await state.update_data(age=message.text)

    # Готовим данные к выводу
    user_data = await state.get_data()
    name = user_data.get('name')
    age = user_data.get('age')

    # Отправляем данные юзеру
    await message.answer(
        f'Круто, {name}! {age} лучший возраст!'
    )

    # Выходим из контекстного состояния FMS
    await state.clear()


@dp.message(F.content_type == types.ContentType.PHOTO)
async def process_image(message: types.Message):
    """Возвращение юзеру размеров, отправленного им изображения."""
    photo = message.photo[-1]
    width = photo.width
    height = photo.height
    await message.answer(
        f'Размер вашего изображения: {width} x {height} пикселей.'
    )


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
