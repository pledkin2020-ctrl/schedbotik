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
    "Числитель": {
        "Понедельник": "Математика, Физика",
        "Вторник": "История, Химия",
        "Среда": "Русский язык, Биология",
        # и так далее
    },
    "Знаменатель": {
        "Понедельник": "География, Физкультура",
        "Вторник": "Английский, Литература",
        "Среда": "Информатика, Музыка",
        # и так далее
    }
}

# Список зачётов
zachety_list = [
    "Тестовый зачёт",
]


@dp.message(Command(commands=["update_schedule"]))
async def update_schedule(message: types.Message):
    """
    Обновляет расписание сразу на всю неделю.
    Формат:
    /update_schedule <числитель/знаменатель>
    день: предмет1, предмет2
    день: предмет1, предмет2
    ...

    Пример:
    /update_schedule числитель
    понедельник: Математика, Физика
    вторник: История, Химия
    """
    text = message.text.replace("/update_schedule", "").strip()

    if not text:
        await message.reply(
            "❌ Укажи тип недели: 'числитель' или 'знаменатель', а затем расписание для всех дней."
        )
        return

    # Разделяем первую строку (тип недели) и остальной текст
    lines = text.split("\n")
    week_type = lines[0].strip().lower()

    if week_type not in schedule:
        await message.reply("❌ Недопустимый тип недели. Используй 'числитель' или 'знаменатель'.")
        return

    # Обрабатываем строки с днями недели
    updated_days = []
    for line in lines[1:]:
        if ":" not in line:
            continue
        day, lessons = line.split(":", 1)
        day = day.strip().lower()
        lessons = lessons.strip()
        if day in schedule[week_type]:
            schedule[week_type][day] = lessons
            updated_days.append(day.capitalize())

    if updated_days:
        await message.reply(f"✅ Расписание для {week_type} обновлено на следующие дни:\n" + ", ".join(updated_days))
    else:
        await message.reply("❌ Не найдено корректных дней для обновления. Проверь формат команд.")

@dp.message(Command(commands=["del_zachet"]))
async def del_zachet(message: types.Message):
    """
    Удаляет предмет/зачёт из списка zachety_list через сообщение.
    Использование: /del_zachet <название зачёта>
    """
    # Убираем команду из текста
    text = message.text.replace("/del_zachet", "").strip()

    if not text:
        await message.reply("❌ Укажи название зачёта после команды. Например:\n/del_zachet Физкультура")
        return

    if text in zachety_list:
        zachety_list.remove(text)
        await message.reply(f"✅ Зачёт '{text}' удалён из списка.")
    else:
        await message.reply(f"❌ Зачёт '{text}' не найден в списке.")

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