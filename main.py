import asyncio
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

TOKEN = "8599743564:AAFYd1AoPNiPlqkzENvMYnjOR2JEXTUQczY"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Пример расписания
schedule = {
    "15.12.2025": "📚 Математика\n📖 История\n🧪 Химия",
    "16.12.2025": "📘 Русский язык\n🌍 География",
}


@dp.message()
async def handle_message(message: Message):
    if not message.text:
        return

    text = message.text.lower()

    # Проверяем, что бота тегнули
    me = await bot.me()
    if f"@{me.username.lower()}" not in text:
        return

    # Ищем дату
    match = re.search(r"(\d{1,2}\.\d{1,2})", text)
    if not match:
        await message.reply("📅 Укажи дату в формате ДД.ММ")
        return

    date = match.group(1)
    year = datetime.now().year
    full_date = f"{date}.{year}"

    if full_date in schedule:
        await message.reply(
            f"🗓 Расписание на {date}:\n\n{schedule[full_date]}"
        )
    else:
        await message.reply(f"❌ Расписание на {date} не найдено")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())