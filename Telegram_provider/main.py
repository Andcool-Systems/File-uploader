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
import fileuploader

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
        try:
            user_obj = await fileuploader.User.loginToken(user.token)
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Log out",
                callback_data=f"logout")
            )

            await message.answer(f"*Account:*\n*Username:* {user_obj.username}\n",
                                reply_markup=builder.as_markup(), 
                                parse_mode="Markdown")
        except fileuploader.exceptions.NotAuthorized:
            await db.user.delete(where={"id": user.id})
            await send_login_message(message)
            return
        except fileuploader.exceptions.TooManyRequests:
            await message.answer("Sorry, the servers are overloaded right now")
            return


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

    try:
        if login_register == 'login':
            user = await fileuploader.User.login(login_and_password[0], login_and_password[1])
        else:
            user = await fileuploader.User.register(login_and_password[0], login_and_password[1])
        
        await db.user.create(data={
                    "user_id": message.from_user.id,
                    "username": user.username,
                    'token': user.accessToken
        })
        await account(message, state)
        await state.clear()
        return
    except fileuploader.exceptions.UserAreadyRegistered:
        await message.answer("User with this username was already registered")
        return
    except fileuploader.exceptions.WrongPassword:
        await message.answer("Wrong password")
        return
    except fileuploader.exceptions.UserNotFound:
        await message.answer("User not found")
        return
    finally:
        await message.delete()


@dp.callback_query(F.data == "logout")
async def log(callback: types.CallbackQuery, state: FSMContext):
    user_db = await db.user.find_first(where={"user_id": callback.from_user.id})
    if not user_db:
        await callback.message.answer("You are not logged in")
        return

    user = fileuploader.User.User()
    user.accessToken = user_db.token
    try:
        await user.logout()
    finally:
        await db.user.delete(where={"id": user_db.id})
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
    user_obj = fileuploader.User.User(user.token)

    try:
        file = await fileuploader.upload(file_bytes, filename, user=user_obj)
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="Delete file",
            callback_data=f"delete_{file.file_url}_{file.key}")
        )

        await message.reply(f"*Your file has been uploaded.!*\n*Link:* {file.file_url_full}\n*Size:* {file.size}", 
                            reply_markup=builder.as_markup(), 
                            parse_mode="Markdown")
        
    except fileuploader.exceptions.FileSizeExceedsTheLimit:
        await message.reply("File size exceeds the limit (100MB)")
        return
    except fileuploader.exceptions.InvalidGroup:
        await message.reply("Invalid group")
        return
    except fileuploader.exceptions.GroupNotFound:
        await message.reply("Group not found")
        return
    except fileuploader.exceptions.YouAreNotInTheGroup:
        await message.reply("You are not in the group")
        return


@dp.callback_query(F.data.startswith("delete_"))
async def delete_file(callback: types.CallbackQuery, state: FSMContext):
    """Хэндлер для колбэка кнопок выбора удаления"""

    file_data = callback.data.replace("delete_", "").split("_")
    try:
        await fileuploader.delete(file_data[0], file_data[1])
        await callback.message.delete()
        await callback.message.answer("File has been deleted!")
    
    except fileuploader.exceptions.FileNotFound:
        await callback.message.answer("File not found")
    except fileuploader.exceptions.InvalidUniqueKey:
        await callback.message.answer("Error while deleting file")

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
