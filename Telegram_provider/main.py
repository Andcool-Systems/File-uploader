"""
by AndcoolSystems, 2024
"""

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.methods import DeleteWebhook
from prisma import Prisma
import os
from dotenv import load_dotenv
import time
import asyncio
import io
import aiohttp

"""Создание всех нужных объектов"""
load_dotenv()
bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher()
db = Prisma()
version = "beta 0.0.1"

class States(StatesGroup):
    """Стейты для aiogram"""

    wait_to_data = State()
    login_register = State()


async def upload(bytes: bytearray, filename: str, user):
    form_data = aiohttp.FormData()
    form_data.add_field('file', bytes, filename=filename)
    headers = {}
    if user:
        headers = {"Authorization": "Bearer " + user.token}

    async with aiohttp.ClientSession("https://fu.andcool.ru") as session:
        async with session.post(f"/api/upload/private", 
                                data=form_data, headers=headers) as r:
            return r, await r.json()


async def get_files(token: str):
    async with aiohttp.ClientSession("https://fu.andcool.ru") as session:
        async with session.get(f"/api/get_files/private", headers={"Authorization": "Bearer " + token}) as r:
            return r, await r.json()
        

async def send_login_message(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Log in",
        callback_data=f"log_login")
    )
    builder.add(types.InlineKeyboardButton(
        text="Register",
        callback_data=f"log_register")
    )

    await message.answer(f"_To access your files from any device, sign in. " + \
                            "The files will be linked to your account and you will have full access to them._", 
                        reply_markup=builder.as_markup(), 
                        parse_mode="Markdown")


@dp.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    """Хэндлер для команды /start"""

    await state.clear()
    await message.answer("*Attention! This bot is in open beta testing, so there may be significant bugs and errors in operation.\n*" + \
                         f"Current version: {version}", parse_mode="Markdown")
    await message.answer(f"Hello, {message.from_user.full_name}!\n" + \
                         f"I am the Telegram provider of the fu.andcool.ru service. To get started, send me the file that needs to be uploaded.")
    

@dp.message(Command('account'))
async def account(message: types.Message, state: FSMContext):
    user = await db.user.find_first(where={"user_id": message.from_user.id})
    if not user:
        await send_login_message(message)
        return
        
    else:
        response, response_json = await get_files(user.token)
        if response.status == 401:
            await db.user.delete(where={"id": user.id})
            await send_login_message(message)
            return
        
        if response.status == 429:
            await message.answer("Sorry, the servers are overloaded right now")
            return
 
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="Log out",
            callback_data=f"logout")
        )

        await message.answer(f"*Account:*\n*Username:* {user.username}\n" + \
                              f"*Files on account:* {len(response_json['data'])}", 
                            reply_markup=builder.as_markup(), 
                            parse_mode="Markdown")


@dp.callback_query(F.data.startswith("log_"))
async def log(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(f"OK, now send me the data from your account in the format:\n```\nMy cool username\nMy cool password```", 
                                parse_mode="Markdown")
    await state.set_state(States.wait_to_data)
    await state.update_data(login_register=callback.data.replace("log_", ""))


@dp.message(F.text, States.wait_to_data)
async def log_reg(message: types.Message, state: FSMContext):
    login_register = (await state.get_data())["login_register"]
    login_and_password = message.text.replace('`', '').split("\n")

    if len(login_and_password) < 2:
        await message.answer('The data was sent incorrectly')
        return

    async with aiohttp.ClientSession("https://fu.andcool.ru") as session:
        async with session.post(f"/api/{'login' if login_register == 'login' else 'register'}?bot=true", 
                                json={"username": login_and_password[0],
                                      "password": login_and_password[1]}) as r:
            
            await message.delete()
            data_resp = await r.json()
            if r.status == 400 or r.status == 404:
                await message.answer(data_resp['message'])
                return
            
            if r.status == 200:
                await db.user.create(data={
                    "user_id": message.from_user.id,
                    "username": data_resp['username'],
                    'token': data_resp['accessToken']
                })
                await account(message, state)
                await state.clear()
                return

            await message.answer("Unhandled error")
            return


@dp.callback_query(F.data == "logout")
async def log(callback: types.CallbackQuery, state: FSMContext):
    user = await db.user.find_first(where={"user_id": callback.from_user.id})
    if not user:
        await callback.message.answer("You are not logged in")
        return

    async with aiohttp.ClientSession("https://fu.andcool.ru") as session:
        async with session.get(f"/api/logout", headers={"Authorization": "Bearer " + user.token}) as response:
            if response.status == 401 or response.status == 200:
                await db.user.delete(where={"id": user.id})
                await callback.message.answer("Logged out!")
                await callback.message.delete()
                return


@dp.message(F.content_type.in_({'document', 'photo', 'video', 'animation', 'video_note', 'voice', 'text'}))
async def send_file(message: types.Message, state: FSMContext):
    """Хэндлер для файлов"""

    match message.content_type:
        case "document":
            document = message.document
            file_id = document.file_id

            bio = io.BytesIO()
            filename = document.file_name
            file_bytes = await bot.download(file_id, destination=bio)
            bio.seek(0)

        case "photo":
            photo = message.photo[-1]
            file_id = photo.file_id
            file = await bot.get_file(file_id)

            bio = io.BytesIO()
            filename = file.file_path
            file_bytes = await bot.download(file_id, destination=bio)
            bio.seek(0)

        case "video":
            video = message.video
            file_id = video.file_id
            file = await bot.get_file(file_id)

            bio = io.BytesIO()
            filename = file.file_path
            file_bytes = await bot.download(file_id, destination=bio)
            bio.seek(0)

        case "animation":
            animation = message.animation
            file_id = animation.file_id
            file = await bot.get_file(file_id)

            bio = io.BytesIO()
            filename = file.file_path
            file_bytes = await bot.download(file_id, destination=bio)
            bio.seek(0)

        case "video_note":
            video_note = message.video_note
            file_id = video_note.file_id
            file = await bot.get_file(file_id)

            bio = io.BytesIO()
            filename = file.file_path
            file_bytes = await bot.download(file_id, destination=bio)
            bio.seek(0)

        case "voice":
            voice = message.voice
            file_id = voice.file_id
            file = await bot.get_file(file_id)

            bio = io.BytesIO()
            filename = f"voice.mp3"
            file_bytes = await bot.download(file_id, destination=bio)
            bio.seek(0)

        case "text":
            file_bytes = message.text.encode()
            filename = 'text.txt'

    user = await db.user.find_first(where={"user_id": message.from_user.id})
    response, result = await upload(file_bytes, filename, user)

    if response.status != 200:
        error = result['error'] if response.status == 429 else result['message']
        await message.reply(error)
        return

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Delete file",
        callback_data=f"delete_{result['file_url']}_{result['key']}")
    )

    await message.reply(f"*Your file has been uploaded.!*\n*Link:* {result['file_url_full']}\n*Size:* {result['size']}", 
                        reply_markup=builder.as_markup(), 
                        parse_mode="Markdown")


@dp.callback_query(F.data.startswith("delete_"))
async def delete_file(callback: types.CallbackQuery, state: FSMContext):
    """Хэндлер для колбэка кнопок выбора удаления"""

    file_data = callback.data.replace("delete_", "").split("_")
    async with aiohttp.ClientSession("https://fu.andcool.ru") as session:
        async with session.get(f"/api/delete/{file_data[0]}?key={file_data[1]}") as r:
            response = await r.json()
            if response['status'] == 'success':
                await callback.message.delete()
                await callback.message.answer("File has been deleted!")
            else:
                await callback.message.answer(response['message'])


async def start():
    """Асинхронная функция для запуска диспатчера"""
    
    await db.connect()  # Connecting to database
    started = True
    while started:
        try:
            await bot(DeleteWebhook(drop_pending_updates=True))
            await dp.start_polling(bot)
            started = False
        except Exception:
            started = True
            print("An error has occurred, reboot in 10 seconds")
            time.sleep(10)
            print("rebooting...")


if __name__ == '__main__':
    asyncio.run(start())
