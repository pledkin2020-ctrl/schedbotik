import asyncio
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

TOKEN = "8599743564:AAFYd1AoPNiPlqkzENvMYnjOR2JEXTUQczY"

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def main():
    # Загружаем данные при старте бота
    load_schedule()   # загружает расписание из schedule.txt
    load_zachety()    # загружает список зачётов из zachety.txt

    print("Бот запущен! Расписание и зачёты загружены.")  # для отладки
    await dp.start_polling(bot)


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

#система оповещений
chats_to_notify = []

def load_chats():
    global chats_to_notify
    chats_to_notify = []
    try:
        with open("chats.txt", "r", encoding="utf-8") as f:
            chats_to_notify = [int(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        chats_to_notify = []

def save_chats():
    with open("chats.txt", "w", encoding="utf-8") as f:
        for chat_id in chats_to_notify:
            f.write(f"{chat_id}\n")



@dp.message(Command(commands=["broadcast"]))
async def broadcast_message(message: types.Message):
    """
    Рассылает текст во все зарегистрированные чаты
    Формат: /broadcast текст сообщения
    """
    load_chats()
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.reply("❌ Укажи текст сообщения после команды.\nПример:\n/broadcast Привет всем!")
        return

    sent_count = 0
    for chat_id in chats_to_notify:
        try:
            await bot.send_message(chat_id, text)
            sent_count += 1
        except Exception as e:
            print(f"Не удалось отправить сообщение в чат {chat_id}: {e}")

    await message.reply(f"✅ Сообщение отправлено в {sent_count} чат(ов).")

@dp.message(Command(commands=["register_chat"]))
async def register_chat(message: types.Message):
    """
    Регистрирует текущий чат для рассылки сообщений и ежедневного расписания
    """
    chat_id = message.chat.id
    load_chats()
    if chat_id in chats_to_notify:
        await message.reply("✅ Этот чат уже зарегистрирован для рассылки.")
        return

    chats_to_notify.append(chat_id)
    save_chats()
    await message.reply("✅ Чат успешно зарегистрирован для рассылки сообщений!")


# Список зачётов
zachety_list = [
    "Тестовый зачёт",
]

def save_schedule():
    """
    Сохраняет текущий словарь schedule в файл schedule.txt
    """
    with open("schedule.txt", "w", encoding="utf-8") as f:
        for week_type in ["числитель", "знаменатель"]:
            f.write(f"[{week_type}]\n")
            for day, lessons in schedule[week_type].items():
                f.write(f"{day}: {lessons}\n")
            f.write("\n")

@dp.message(Command(commands=["clear_zachety"]))
async def clear_zachety(message: types.Message):
    """
    Очищает все зачёты и сохраняет пустой список в zachety.txt
    """
    global zachety_list
    load_zachety()  # загружаем актуальный список

    if not zachety_list:
        await message.reply("❌ Список зачётов уже пустой.")
        return

    zachety_list.clear()  # очищаем список
    save_zachety()         # сохраняем пустой список в файл
    await message.reply("✅ Все зачёты удалены из списка.")

@dp.message(Command(commands=["clear_schedule"]))
async def clear_schedule(message: types.Message):
    """
    Очищает все расписания (числитель и знаменатель) и сохраняет в schedule.txt
    """
    load_schedule()  # загружаем текущее расписание

    # Очищаем все дни в обеих неделях
    for week_type in schedule:
        for day in schedule[week_type]:
            schedule[week_type][day] = ""

    save_schedule()  # сохраняем пустое расписание в файл
    await message.reply("✅ Всё расписание очищено.")

@dp.message(Command(commands=["help"]))
async def send_help(message: types.Message):
    help_text = (
        "🤖 Доступные команды бота:\n\n"
        "/schedule <числитель/знаменатель> — показать расписание на неделю\n"
        "/zachety — показать список зачётов\n"
        "/help — показать это сообщение\n\n"
    )
    await message.reply(help_text)

@dp.message(Command(commands=["update_schedule"]))
async def update_schedule(message: types.Message):
    """
    Обновляет расписание на всю неделю через чат и сохраняет в schedule.txt
    Формат:
    /update_schedule <числитель/знаменатель>
    день: предмет1, предмет2
    день: предмет1, предмет2
    ...

    Пример:
    /update_schedule числитель
    понедельник: Математика, Физика
    вторник: История, Химия
    среда: Русский язык, Биология
    четверг: География, Литература
    пятница: Английский, Информатика
    суббота: Физкультура
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

    # Загружаем текущее расписание из файла перед обновлением
    load_schedule()

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

    # Сохраняем изменения в файл
    save_schedule()

    if updated_days:
        await message.reply(f"✅ Расписание для {week_type} обновлено на следующие дни:\n" + ", ".join(updated_days))
    else:
        await message.reply("❌ Не найдено корректных дней для обновления. Проверь формат команды.")

# ------------------ Работа с файлом зачётов ------------------

def load_zachety():
    """
    Загружает список зачётов из zachety.txt
    """
    global zachety_list
    zachety_list = []
    try:
        with open("zachety.txt", "r", encoding="utf-8") as f:
            zachety_list = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Файл zachety.txt не найден, создается пустой список")
        zachety_list = []

def save_zachety():
    """
    Сохраняет список зачётов в zachety.txt
    """
    with open("zachety.txt", "w", encoding="utf-8") as f:
        for item in zachety_list:
            f.write(item + "\n")

@dp.message(Command(commands=["zachety"]))
async def send_zachety(message: types.Message):
    load_zachety()  # загружаем актуальный список
    if not zachety_list:
        await message.reply("❌ Список зачётов пустой")
        return

    reply_text = "📝 Список зачётов:\n\n"
    for item in zachety_list:
        reply_text += f"• {item}\n"
    await message.reply(reply_text)

@dp.message(Command(commands=["add_zachet"]))
async def add_zachet(message: types.Message):
    text = message.text.replace("/add_zachet", "").strip()
    if not text:
        await message.reply("❌ Укажи название зачёта после команды.\nПример:\n/add_zachet Физкультура")
        return

    load_zachety()
    zachety_list.append(text)
    save_zachety()
    await message.reply(f"✅ Зачёт '{text}' добавлен в список.")

@dp.message(Command(commands=["del_zachet"]))
async def del_zachet(message: types.Message):
    text = message.text.replace("/del_zachet", "").strip()
    if not text:
        await message.reply("❌ Укажи название зачёта после команды.\nПример:\n/del_zachet История")
        return

    load_zachety()
    if text in zachety_list:
        zachety_list.remove(text)
        save_zachety()
        await message.reply(f"✅ Зачёт '{text}' удалён из списка.")
    else:
        await message.reply(f"❌ Зачёт '{text}' не найден в списке.")
# вызываем
schedule = {}

def load_schedule():
    """
    Загружает расписание из файла schedule.txt
    """
    global schedule
    schedule = {"числитель": {}, "знаменатель": {}}
    current_week = None
    try:
        with open("schedule.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current_week = line[1:-1].lower()
                    continue
                if current_week and ":" in line:
                    day, lessons = line.split(":", 1)
                    schedule[current_week][day.strip().lower()] = lessons.strip()
    except FileNotFoundError:
        print("Файл schedule.txt не найден, создается пустой словарь")
# --- Добавляем эту функцию в main.py ---

@dp.message(Command(commands=["schedule"]))
async def send_schedule(message: types.Message):
    """
    Показывает расписание на всю неделю, читая данные из schedule.txt
    Использование: /schedule числитель или /schedule знаменатель
    """
    load_schedule()  # Загружаем актуальное расписание из файла при каждом вызове
    text = message.text.lower().replace("/schedule", "").strip()

    if text not in ["числитель", "знаменатель"]:
        await message.reply(
            "📅 Укажи тип недели: 'числитель' или 'знаменатель'.\n"
            "Пример:\n/schedule числитель"
        )
        return

    week_schedule = schedule.get(text)
    reply_text = f"🗓 Расписание на неделю ({text}):\n\n"

    for day, lessons in week_schedule.items():
        reply_text += f"{day.capitalize()}: {lessons}\n"

    await message.reply(reply_text)

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