import asyncio
import re
from datetime import datetime
import json
from html import escape

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

TOKEN = "8599743564:AAEe9noSFLa1Edp1p3MWuDpv4F0cz1Sd8rs"
ADMINS_FILE = "admins.txt"
admins = set()

def load_admins():
    admins.clear()
    try:
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        admins.add(int(line))
                    except ValueError:
                        pass
    except FileNotFoundError:
        open(ADMINS_FILE, "w").close()

def save_admins():
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        for a in admins:
            f.write(f"{a}\n")

def is_admin(message: types.Message) -> bool:
    return message.from_user.id in admins

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def main():
    # Загружаем данные при старте бота
    load_schedule()   # загружает расписание из schedule.txt
    load_zachety()    # загружает список зачётов из zachety.txt
    load_chats()
    load_week()
    load_admins()
    load_autosend()

    asyncio.create_task(daily_scheduler())
    asyncio.create_task(autosend_loop())

    async def run_task(coro):
        while True:
            try:
                await coro()
            except Exception as e:
                print(f"Ошибка в таске {coro.__name__}: {e}")
                await asyncio.sleep(5)

    print("Бот запущен! Расписание и зачёты загружены.")  # для отладки
    await dp.start_polling(bot)

#тестим1
@dp.message()
async def handle_text(message: types.Message):
    if not message.text:
        return

    text = message.text.lower().strip()

    # "сегодня" — показать расписание на сегодня
    if "сегодня" in text:
        await message.reply(get_today_schedule())
        return

    # "какая сейчас неделя" — показать текущую неделю
    if "какая сейчас неделя" in text:
        current_week = load_week()
        await message.reply(f"📅 Сейчас {current_week} неделя")
        return

    # "расписание" — показать расписание на сегодня
    if "расписание" in text:
        await message.reply(get_today_schedule())
        return

    # "зачёт" — показать список зачётов
    if "зачёт" in text:
        load_zachety()
        if zachety_list:
            reply_text = "📝 Список зачётов:\n\n" + "\n".join(f"• {item}" for item in zachety_list)
        else:
            reply_text = "❌ Список зачётов пустой"
        await message.reply(reply_text)
        return
#тестим
@dp.message(Command(commands=["all"]))
async def mention_all(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Эта команда работает только в группах или супергруппах.")
        return

    text_to_send = message.text.replace("/all", "").strip()
    if not text_to_send:
        await message.reply("❌ Укажи текст сообщения после команды.\nПример:\n/all Всем привет!")
        return

    try:
        me = await bot.get_me()  # получаем данные бота
        members = await bot.get_chat_administrators(message.chat.id)
        mentions = []

        for member in members:
            user = member.user
            if user.id == me.id:
                continue  # пропускаем самого бота
            name = escape(user.first_name)
            mentions.append(f'<a href="tg://user?id={user.id}">{name}</a>')

        mentions_text = " ".join(mentions)
        final_text = f"{text_to_send}\n\n{mentions_text}"
        await bot.send_message(message.chat.id, final_text, parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Не удалось получить участников чата: {e}")
# ------------------ Работа с чатами для рассылки ------------------

@dp.message(Command(commands=["chats"]))
async def list_chats(message: types.Message):
    if not is_admin(message):
        await message.reply("❌ Нет прав для этой команды")
        return

    load_chats()
    if not chats_to_notify:
        await message.reply("ℹ️ Список зарегистрированных чатов пуст.")
        return

    reply_text = "📋 Зарегистрированные чаты для рассылки:\n"
    for chat_id in chats_to_notify:
        reply_text += f"• {chat_id}\n"
    await message.reply(reply_text)


@dp.message(Command(commands=["addchat"]))
async def add_chat(message: types.Message):
    if not is_admin(message):
        await message.reply("❌ Нет прав для этой команды")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.reply("❌ Используй: /addchat <chat_id>")
        return

    try:
        chat_id = int(args[1])
    except ValueError:
        await message.reply("❌ Некорректный chat_id")
        return

    load_chats()
    if chat_id in chats_to_notify:
        await message.reply("ℹ️ Этот чат уже зарегистрирован")
        return

    chats_to_notify.append(chat_id)
    save_chats()
    await message.reply(f"✅ Чат {chat_id} добавлен в список рассылки")


@dp.message(Command(commands=["delchat"]))
async def del_chat(message: types.Message):
    if not is_admin(message):
        await message.reply("❌ Нет прав для этой команды")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.reply("❌ Используй: /delchat <chat_id>")
        return

    try:
        chat_id = int(args[1])
    except ValueError:
        await message.reply("❌ Некорректный chat_id")
        return

    load_chats()
    if chat_id not in chats_to_notify:
        await message.reply("❌ Чат не найден в списке рассылки")
        return

    chats_to_notify.remove(chat_id)
    save_chats()
    await message.reply(f"✅ Чат {chat_id} удалён из списка рассылки")
# ------------------ Команда для проверки времени бота ------------------
@dp.message(Command(commands=["time"]))
async def bot_time(message: types.Message):
    now = datetime.now()
    await message.reply(f"⏰ Текущее время бота: {now.strftime('%Y-%m-%d %H:%M:%S')}")
#заливаем авторассылку
AUTOSEND_FILE = "autosend.json"

autosend_settings = {
    "enabled": False,
    "time": "07:00",
    "content": "today+week",
    "last_sent": ""
}

def load_autosend():
    global autosend_settings
    try:
        with open(AUTOSEND_FILE, "r", encoding="utf-8") as f:
            autosend_settings = json.load(f)
    except FileNotFoundError:
        save_autosend()

def save_autosend():
    with open(AUTOSEND_FILE, "w", encoding="utf-8") as f:
        json.dump(autosend_settings, f, ensure_ascii=False, indent=2)


async def autosend_loop():
    while True:
        load_autosend()

        if not autosend_settings["enabled"]:
            await asyncio.sleep(30)
            continue

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        today_date = now.strftime("%Y-%m-%d")

        if (
            current_time == autosend_settings["time"]
            and autosend_settings["last_sent"] != today_date
        ):
            load_chats()

            if autosend_settings["content"] == "today":
                text = get_today_schedule()
            elif autosend_settings["content"] == "week":
                text = get_week_schedule()
            else:
                text = get_today_schedule() + "\n\n" + get_week_schedule()

            for chat_id in chats_to_notify:
                try:
                    await bot.send_message(chat_id, text, parse_mode=None)
                except Exception as e:
                    print(f"Ошибка авторассылки в {chat_id}: {e}")

            autosend_settings["last_sent"] = today_date
            save_autosend()

            await asyncio.sleep(60)

        await asyncio.sleep(20)

@dp.message(Command("autosend"))
async def autosend_cmd(message: types.Message):
    if not is_admin(message):
        await message.reply("❌ Нет прав")
        return

    load_autosend()
    args = message.text.split()

    if len(args) == 1:
        await message.reply(
            "⚙️ Использование:\n"
            "/autosend on | off\n"
            "/autosend time HH:MM\n"
            "/autosend content today | week | today+week\n"
            "/autosend status"
        )
        return

    sub = args[1].lower()

    # on / off
    if sub in ("on", "off"):
        autosend_settings["enabled"] = sub == "on"
        save_autosend()
        await message.reply(f"📡 Авторассылка {'включена' if sub == 'on' else 'выключена'}")
        return

    # time
    if sub == "time":
        if len(args) != 3 or not re.match(r"^\d{2}:\d{2}$", args[2]):
            await message.reply("❌ Формат: /autosend time HH:MM")
            return
        autosend_settings["time"] = args[2]
        save_autosend()
        await message.reply(f"⏰ Время авторассылки установлено: {args[2]}")
        return

    # content
    if sub == "content":
        if len(args) != 3 or args[2] not in ("today", "week", "today+week"):
            await message.reply("❌ Используй: today | week | today+week")
            return
        autosend_settings["content"] = args[2]
        save_autosend()
        await message.reply(f"📦 Контент авторассылки: {args[2]}")
        return

    # status
    if sub == "status":
        status = "ВКЛ ✅" if autosend_settings["enabled"] else "ВЫКЛ ❌"
        await message.reply(
            f"📡 Авторассылка: {status}\n"
            f"⏰ Время: {autosend_settings['time']}\n"
            f"📦 Контент: {autosend_settings['content']}\n"
            f"📅 Последняя отправка: {autosend_settings['last_sent'] or 'ещё не было'}"
        )
        return

    await message.reply("❌ Неизвестная подкоманда")

#заливаем админов
@dp.message(Command("addadmin"))
async def add_admin(message: types.Message):
    if not is_admin(message):
        await message.reply("❌ Нет прав")
        return
    try:
        new_id = int(message.text.replace("/addadmin", "").strip())
    except ValueError:
        await message.reply("❌ Введите корректный ID")
        return

    if new_id in admins:
        await message.reply("ℹ️ Пользователь уже админ")
        return

    admins.add(new_id)
    save_admins()
    await message.reply(f"✅ Пользователь {new_id} добавлен как админ")

@dp.message(Command("deladmin"))
async def del_admin(message: types.Message):
    if not is_admin(message):
        await message.reply("❌ Нет прав")
        return
    try:
        rem_id = int(message.text.replace("/deladmin", "").strip())
    except ValueError:
        await message.reply("❌ Введите корректный ID")
        return

    if rem_id in admins:
        admins.remove(rem_id)
        save_admins()
        await message.reply(f"✅ Пользователь {rem_id} удалён из админов")
    else:
        await message.reply("❌ Пользователь не найден в списке админов")

#заливаем недели
WEEK_FILE = "week.txt"


def load_week():
    try:
        with open(WEEK_FILE, "r", encoding="utf-8") as f:
            week = f.read().strip().lower()
            if week in ("числитель", "знаменатель"):
                return week
    except FileNotFoundError:
        pass
    save_week("числитель")
    return "числитель"


def save_week(week: str):
    with open(WEEK_FILE, "w", encoding="utf-8") as f:
        f.write(week)


def switch_week():
    current = load_week()
    new_week = "знаменатель" if current == "числитель" else "числитель"
    save_week(new_week)
    return new_week
#встраиваем админку
@dp.message(Command(commands=["myid"]))
async def my_id(message: types.Message):
    await message.reply(f"Ваш user_id: {message.from_user.id}")

def is_admin(message: types.Message) -> bool:
    return message.from_user.id in admins
#встраиваем автосообщение
@dp.message(Command(commands=["setweek"]))
async def setweek_cmd(message: types.Message):
    if not is_admin(message):
        await message.reply("❌ Нет прав")
        return

    text = message.text.replace("/setweek", "").strip().lower()
    if text not in ("числитель", "знаменатель"):
        await message.reply("❌ Используй: /setweek числитель | знаменатель")
        return

    save_week(text)
    await message.reply(f"✅ Текущая неделя установлена: {text}")


from datetime import datetime

def get_today_schedule():
    week = load_week()
    today = datetime.now().strftime("%A").lower()

    days_map = {
        "monday": "понедельник",
        "tuesday": "вторник",
        "wednesday": "среда",
        "thursday": "четверг",
        "friday": "пятница",
        "saturday": "суббота",
        "sunday": "воскресенье",
    }

    day_ru = days_map.get(today)
    load_schedule()

    lessons = schedule.get(week, {}).get(day_ru, "")
    if not lessons:
        return f"📅 Сегодня ({day_ru})\nПар нет 🎉"

    return f"📅 Сегодня ({day_ru})\n\n{lessons}"


async def daily_scheduler():
    while True:
        now = datetime.now()

        # 07:00 — отправка расписания
        if now.time().hour == 7 and now.time().minute == 0:
            load_chats()
            text = get_today_schedule() + "\n\n" + get_week_schedule()

            for chat_id in chats_to_notify:
                try:
                    await bot.send_message(chat_id, text, parse_mode=None)
                except Exception as e:
                    print(f"Ошибка отправки в {chat_id}: {e}")

            await asyncio.sleep(60)

        # Понедельник 00:00 — переключение недели
        if now.weekday() == 0 and now.time().hour == 0 and now.time().minute == 0:
            new_week = switch_week()
            print(f"Неделя автоматически переключена на {new_week}")
            await asyncio.sleep(60)

        await asyncio.sleep(30)

@dp.message(Command("today"))
async def today_cmd(message: types.Message):
    await message.reply(get_today_schedule(), parse_mode=None)



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
    if not is_admin(message):
        await message.reply("❌ У вас нет прав для этой команды", parse_mode=None)
        return
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
    if not is_admin(message):
        await message.reply("❌ У вас нет прав для этой команды", parse_mode=None)
        return
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
    Сохраняет расписание в schedule.txt (корректный многострочный формат)
    """
    with open("schedule.txt", "w", encoding="utf-8") as f:
        for week_type in ("числитель", "знаменатель"):
            f.write(f"[{week_type}]\n")
            for day, lessons in schedule[week_type].items():
                f.write(f"{day}:\n")
                if lessons:
                    for line in lessons.split("\n"):
                        f.write(f"{line}\n")
                f.write("\n")

@dp.message(Command(commands=["clear_zachety"]))
async def clear_zachety(message: types.Message):
    if not is_admin(message):
        await message.reply("❌ У вас нет прав для этой команды", parse_mode=None)
        return
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
    if not is_admin(message):
        await message.reply("❌ У вас нет прав для этой команды", parse_mode=None)
        return
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
    if not is_admin(message):
        await message.reply("❌ У вас нет прав для этой команды")
        return

    load_schedule()

    text = message.text.replace("/update_schedule", "", 1).strip()
    if not text:
        await message.reply(
            "❌ Формат:\n"
            "/update_schedule числитель\n"
            "понедельник:\n"
            "1) Математика\n"
            "2) Физика"
        )
        return

    lines = [line.rstrip() for line in text.split("\n")]

    week_type = lines[0].lower()
    if week_type not in ("числитель", "знаменатель"):
        await message.reply("❌ Укажи: числитель или знаменатель")
        return

    current_day = None
    buffer = []
    updated_days = []

    for line in lines[1:]:
        line = line.strip()

        if not line:
            continue

        # если это новый день
        if line.endswith(":"):
            if current_day:
                schedule[week_type][current_day] = "\n".join(buffer)
                updated_days.append(current_day.capitalize())

            current_day = line[:-1].lower()
            buffer = []
        else:
            buffer.append(line)

    # сохранить последний день
    if current_day:
        schedule[week_type][current_day] = "\n".join(buffer)
        updated_days.append(current_day.capitalize())

    save_schedule()

    if updated_days:
        await message.reply(
            f"✅ Расписание обновлено ({week_type}):\n" +
            ", ".join(updated_days)
        )
    else:
        await message.reply("❌ Не удалось обновить расписание. Проверь формат.")

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
    if not is_admin(message):
        await message.reply("❌ У вас нет прав для этой команды", parse_mode=None)
        return
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
    if not is_admin(message):
        await message.reply("❌ У вас нет прав для этой команды", parse_mode=None)
        return
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
    Загружает расписание из schedule.txt (поддержка многострочных дней)
    """
    global schedule
    schedule = {"числитель": {}, "знаменатель": {}}

    current_week = None
    current_day = None
    buffer = []

    try:
        with open("schedule.txt", "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.rstrip()

                if not line:
                    continue

                # [числитель] или [знаменатель]
                if line.startswith("[") and line.endswith("]"):
                    if current_day and buffer:
                        schedule[current_week][current_day] = "\n".join(buffer)
                        buffer = []

                    current_week = line[1:-1].lower()
                    current_day = None
                    continue

                # новый день
                if line.endswith(":"):
                    if current_day and buffer:
                        schedule[current_week][current_day] = "\n".join(buffer)

                    current_day = line[:-1].lower()
                    buffer = []
                    continue

                # строка пары
                if current_day:
                    buffer.append(line)

            # сохранить последний день
            if current_week and current_day and buffer:
                schedule[current_week][current_day] = "\n".join(buffer)

    except FileNotFoundError:
        print("Файл schedule.txt не найден")
# --- Добавляем эту функцию в main.py ---

@dp.message(Command(commands=["schedule"]))
async def send_schedule(message: types.Message):
    load_schedule()

    week_type = message.text.lower().replace("/schedule", "").strip()
    if week_type not in ("числитель", "знаменатель"):
        await message.reply(
            "📅 Использование:\n"
            "/schedule числитель\n"
            "/schedule знаменатель"
        )
        return

    days_order = [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ]

    reply = f"🗓 Расписание на неделю ({week_type}):\n\n"

    for day in days_order:
        lessons = schedule.get(week_type, {}).get(day)

        reply += f"📌 {day.capitalize()}:\n"
        if lessons:
            reply += lessons + "\n"
        else:
            reply += "Пар нет 🎉\n"
        reply += "\n"

    await message.reply(reply)

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


if __name__ == "__main__":
    asyncio.run(main())