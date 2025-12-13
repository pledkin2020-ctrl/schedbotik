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

# Список зачётов
zachety_list = [
    "Юридическое делопроизводство",
    "История",
    "Химия",
    "Русский язык",
    "География",
    "Физика"
]

@dp.message(Command(commands=["add_zachet"]))
async def add_zachet(message: types.Message):
    """
    Добавляет новый предмет/зачёт в список zachety_list через сообщение.
    Использование: /add_zachet <название зачёта>
    """
    # Убираем команду из текста
    text = message.text.replace("/add_zachet", "").strip()

    if not text:
        await message.reply("❌ Укажи название зачёта после команды. Например:\n/add_zachet Физкультура")
        return

    zachety_list.append(text)
    await message.reply(f"✅ Зачёт '{text}' добавлен в список.")

@dp.message(Command(commands=["zachety"]))
async def send_zachety(message: types.Message):
    """
    Команда /zachety выводит весь список зачётов.
    """
    if not zachety_list:
        await message.reply("❌ Список зачётов пустой")
        return

    reply_text = "📝 Список зачётов:\n\n"
    for item in zachety_list:
        reply_text += f"• {item}\n"

    await message.reply(reply_text)

# --- Добавляем эту функцию в main.py ---

@dp.message(Command(commands=["schedule"]))
async def send_schedule(message: types.Message):
    """
    Обработка команды /schedule.
    Можно писать: /schedule 15.12, /schedule сегодня, /schedule завтра
    """
    text = message.text
    today = datetime.now()

    # Обработка слов "сегодня" и "завтра"
    if "сегодня" in text.lower():
        date_str = today.strftime("%d.%m.%Y")
    elif "завтра" in text.lower():
        date_str = (today + timedelta(days=1)).strftime("%d.%m.%Y")
    else:
        # Ищем дату в формате ДД.ММ
        match = re.search(r"(\d{1,2}\.\d{1,2})", text)
        if match:
            date = match.group(1)
            date_str = f"{date}.{today.year}"
        else:
            await message.reply("📅 Укажи дату в формате ДД.ММ или напиши 'сегодня', 'завтра'")
            return

    # Отправка расписания
    if date_str in schedule:
        await message.reply(f"🗓 Расписание на {date_str[:-5]}:\n\n{schedule[date_str]}")
    else:
        await message.reply(f"❌ Расписание на {date_str[:-5]} не найдено")

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