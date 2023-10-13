import os
import zipfile
import requests
import sqlite3
from bs4 import BeautifulSoup as BS
import aiogram
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Инициализация бота
bot = Bot(token='5720257287:AAH9gJWPUoxTIpQ719U3NQDMy7yqDkspviI')
dp = Dispatcher(bot, storage=MemoryStorage())

# URL страницы для парсинга магазина
shop_url = 'https://universofortnite.com/ru/tienda-de-hoy-en-fortnite/'

# URL страницы для парсинга новостей
news_url = 'https://fortnitenews.com/'

# Отправляем GET-запрос и получаем содержимое страницы магазина
shop_response = requests.get(shop_url)
shop_content = shop_response.content

# Создаем объект BeautifulSoup для парсинга содержимого страницы магазина
shop_soup = BS(shop_content, 'html.parser')

# Находим все элементы с классом 'fnapi-item' (товары в магазине)
shop_items = shop_soup.find_all(class_='fnapi-item')

# Отправляем GET-запрос и получаем содержимое страницы новостей
news_response = requests.get(news_url)
news_content = news_response.content

# Создаем объект BeautifulSoup для парсинга содержимого страницы новостей
news_soup = BS(news_content, 'html.parser')

# Подключение к базе данных SQLite
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Создание таблицы пользователей, если она не существует
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        last_name TEXT
    )
''')

# Создание таблицы отзывов, если она не существует
cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        review_text TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')
conn.commit()


class WriteReview(StatesGroup):
    review = State()


async def send_welcome(message: types.Message):
    photo_path = '1644912199_15-kartinkin-net-p-fortnait-kartinki-16.jpg'
    with open(photo_path, 'rb') as photo:
        await bot.send_photo(message.chat.id, photo, caption="Привет! Чем могу помочь?⛏️", reply_markup=get_keyboard())


def get_keyboard():
    # Создаем пользовательскую клавиатуру с кнопками "Магазин", "Новости", "Регистрация", "Написать отзыв" и "Профиль"
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('Магазин🏪', callback_data='shop'),
        InlineKeyboardButton('Новости📰', callback_data='news'),
        InlineKeyboardButton('Регистрация📝', callback_data='register'),
        InlineKeyboardButton('Написать отзыв✍️', callback_data='write_review'),
        InlineKeyboardButton('Профиль👤', callback_data='profile'),
        InlineKeyboardButton('помощь⌨️', callback_data='help'),
    )
    return keyboard


def get_back_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton('Вернуться назад', callback_data='back'))
    return keyboard


@dp.callback_query_handler(lambda c: c.data == 'help')
async def send_help(callback_query: types.CallbackQuery):
    # Обработчик нажатия кнопки "Магазин"
    await send_help(callback_query.message)


@dp.callback_query_handler(lambda c: c.data == 'shop')
async def handle_shop_callback(callback_query: types.CallbackQuery):
    # Обработчик нажатия кнопки "Магазин"
    await send_images(callback_query.message)


@dp.callback_query_handler(lambda c: c.data == 'news')
async def handle_news_callback(callback_query: types.CallbackQuery):
    # Обработчик нажатия кнопки "Новости"
    await get_news(callback_query.message)


@dp.callback_query_handler(lambda c: c.data == 'register')
async def handle_register_callback(callback_query: types.CallbackQuery):
    # Обработчик нажатия кнопки "Регистрация"
    await register_user(callback_query.from_user, callback_query.message)


@dp.callback_query_handler(lambda c: c.data == 'write_review')
async def handle_write_review_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Check if the user is registered
    user_id = callback_query.from_user.id
    cursor.execute('SELECT id FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    if result is None:
        await bot.send_message(callback_query.message.chat.id,
                               "Вы не зарегистрированы. Пожалуйста, зарегистрируйте аккаунт с помощью кнокпи 'Регистрация📝'.")
    else:
        # Обработчик нажатия кнопки "Написать отзыв"
        await WriteReview.review.set()
        await bot.send_message(callback_query.message.chat.id, "Напишите ваш отзыв🖊️:")


@dp.callback_query_handler(lambda c: c.data == 'profile')
async def handle_profile_callback(callback_query: types.CallbackQuery):
    # Обработчик нажатия кнопки "Профиль"
    await get_user_profile(callback_query.from_user, callback_query.message)


async def register_user(user: types.User, message: types.Message):
    # Регистрация пользователя
    try:
        cursor.execute('INSERT INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                       (user.id, user.username, user.first_name, user.last_name))
        conn.commit()
        await bot.send_message(message.chat.id, "Регистрация прошла успешно✅!")
    except sqlite3.IntegrityError:
        await bot.send_message(message.chat.id, "Вы уже зарегистрированы❌.")


async def get_user_profile(user: types.User, message: types.Message):
    # Получение профиля пользователя из базы данных
    cursor.execute('SELECT id, username, first_name, last_name FROM users WHERE user_id = ?', (user.id,))
    result = cursor.fetchone()

    if result is None:
        await bot.send_message(message.chat.id, "Профиль пользователя не найден❌.")
        return

    user_id, username, first_name, last_name = result

    profile_message = f"ваш айди (который в базе данных): {user_id}\n" \
                      f"Имя пользователя: {username}\n" \
                      f"Имя: {first_name}\n" \
 \
            await bot.send_message(message.chat.id, profile_message)


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handle_message(message: types.Message):
    if message.text == '/start':
        await send_welcome(message)
    else:
        await message.reply("Я не понимаю эту команду. Пожалуйста, используйте кнопки на клавиатуре.⌨",
                            reply_markup=get_back_keyboard())


@dp.callback_query_handler(lambda c: c.data == 'back')
async def handle_back_callback(callback_query: types.CallbackQuery):
    await send_welcome(callback_query.message)


@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    # Отправляем справочное сообщение с описанием доступных команд
    help_message = "Доступные команды:\n/start - начать\n/help - 💀☠️"
    await message.reply(help_message)


@dp.message_handler(commands=['news'])
async def get_news(message: types.Message):
    # Парсинг новостей
    news_titles = news_soup.find_all("h2", class_="post-card__title")
    news_excerpts = news_soup.find_all("p", class_="post-card__excerpt")

    if len(news_titles) == 0 or len(news_excerpts) == 0:
        await bot.send_message(message.chat.id, "Новости не найдены📰.")
        return

    latest_title = news_titles[0].text
    latest_excerpt = news_excerpts[0].text

    photo_url = "https://www.kartinki24.ru/uploads/gallery/main/601/kartinki24_ru_fortnite_106.jpg"  # Замените "URL_фото" на фактический URL вашей фотографии

    response = f"Новости Fortnite:\n\n{latest_title}\n\n{latest_excerpt}"
    await bot.send_photo(chat_id=message.chat.id, photo=photo_url, caption=response)


@dp.message_handler(commands=['shop'])
async def send_images(message: types.Message):
    # Send a loading message
    loading_message = await message.reply("Подождите, загружаю изображения...")

    # Создаем временную папку для сохранения изображений
    temp_folder = 'temp_images'
    os.makedirs(temp_folder, exist_ok=True)

    # Скачиваем и сохраняем изображения магазина во временную папку
    image_paths = []
    for i, item in enumerate(shop_items):
        img = item.find('img')
        if img:
            img_src = img['src']
            image_path = f'{temp_folder}/image_{i}.jpg'
            with open(image_path, 'wb') as f:
                image_data = requests.get(img_src).content
                f.write(image_data)
            image_paths.append(image_path)

    # Создаем ZIP-архив из изображений магазина
    zip_file = 'shop_images.zip'
    with zipfile.ZipFile(zip_file, 'w') as zf:
        for image_path in image_paths:
            zf.write(image_path)

    # Отправляем фото с текстовым сообщением
    photo_url = "https://kartinkin.net/uploads/posts/2022-02/thumbs/1644912214_46-kartinkin-net-p-fortnait-kartinki-49.jpg"  # Замените "URL_фото" на фактический URL вашей фотографии
    caption = "Вот фото магазина:"
    await bot.send_photo(message.chat.id, photo=photo_url, caption=caption)

    # Отправляем ZIP-архив с изображениями магазина пользователю
    with open(zip_file, 'rb') as zf:
        caption = ""
        await bot.send_document(message.chat.id, zf, caption=caption)

    # Удаляем временные файлы и папку
    os.remove(zip_file)
    for image_path in image_paths:
        os.remove(image_path)
    os.rmdir(temp_folder)

    # Remove the loading message
    await loading_message.delete()


@dp.message_handler(state=WriteReview.review)
async def write_review_step2(message: types.Message, state: FSMContext):
    # Получаем данные из состояния
    async with state.proxy() as data:
        review_text = message.text

    # Сохраняем отзыв в базе данных
    cursor.execute('SELECT id FROM users WHERE user_id = ?', (message.from_user.id,))
    user_id = cursor.fetchone()[0]

    cursor.execute('INSERT INTO reviews (user_id, review_text) VALUES (?, ?)', (user_id, review_text))
    conn.commit()

    await bot.send_message(message.chat.id, "Спасибо за ваш отзыв!✅")

    # Завершаем состояние
    await state.finish()



if __name__ == '__main__':
    aiogram.executor.start_polling(dp)
