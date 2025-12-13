import asyncio
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
import os

# Загружаем токен из .env
load_dotenv()
TOKEN = os.getenv("8599743564:AAFYd1AoPNiPlqkzENvMYnjOR2JEXTUQczY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Пример расписания
schedule = {
    "15.12.2025": "📚 Математика\n📖 История\n🧪 Химия",
    "16.12.2025": "📘 Русский язык\n🌍 География",
}


# Функция для получения даты по слову "завтра" или "сегодня"
def parse_date(text: str):
    text = text.lower()
    today = datetime.now()

    if "сегодня" in text:
        return today.strftime("%d.%m.%Y")
    elif "завтра" in text:
        tomorrow = today + timedelta(days=1)
        return tomorrow.strftime("%d.%m.%Y")
    else:
        match = re.search(r"(\d{1,2}\.\d{1,2})", text)
        if match:
            date = match.group(1)
            return f"{date}.{today.year}"
    return None


# Команда /schedule
@dp.message(Command(commands=["schedule"]))
async def send_schedule(message: Message):
    date_str = parse_date(message.text)

    if not date_str:
        await message.reply("📅 Укажи дату в формате ДД.ММ или напиши 'сегодня', 'завтра'")
        return

    if date_str in schedule:
        await message.reply(f"🗓 Расписание на {date_str[:-5]}:\n\n{schedule[date_str]}")
    else:
        await message.reply(f"❌ Расписание на {date_str[:-5]} не найдено")


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())