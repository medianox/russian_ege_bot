# Убиваем все старые процессы перед запуском
import requests
import time
import os
import json
import random
import nest_asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import re
from datetime import date, datetime


TOKEN = "8652125406:AAHYxFtCGzkB_HnFyXs_YBvBlKMIgaxHIrc"


print("Очистка старых сессий бота...")
for i in range(5):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=3)
        time.sleep(1)
        print(f"Попытка {i + 1} выполнена")
    except Exception as e:
        print(f"Попытка {i + 1}: {e}")

print("Старые сессии очищены, запускаем бота...\n")
time.sleep(2)

os.system("pip install python-telegram-bot nest_asyncio -q")

nest_asyncio.apply()

def escape_markdown(text):
    return text.replace('*', '').replace('_', '').replace('`', '')

PICTURES = ["pic1.png", "pic2.png", "pic3.png", "pic4.png", "pic5.png", "pic6.png", "pic7.png", "pic8.png", "pic9.png",
            "pic10.png", "pic11.png", "pic12.png", "pic13.png", "pic14.png"]
available_pictures = list(PICTURES)

# Загрузка заданий для паронимов
with open("tasks.txt", "r", encoding="utf-8") as f:
    lines = [x.strip() for x in f if x.strip()]

tasks = []
for i, line in enumerate(lines):
    if line.startswith("Ответ:"):
        answer = line.replace("Ответ:", "").strip()
        if '|' in answer:
            answer = answer.split('|')[0].strip()
        task_lines = []
        j = i - 1
        while j >= 0 and not lines[j].startswith("Ответ:"):
            line_text = lines[j]
            if not any(x in line_text for x in ['Тип', '№', 'i']):
                if not line_text.replace('.', '').replace('-', '').isdigit():
                    task_lines.insert(0, line_text)
            j -= 1
        tasks.append({"text": "\n".join(task_lines), "answer": answer})

TASKS = [{"text": escape_markdown(t['text']), "answer": t['answer']} for t in tasks]
print(f"Загружено {len(TASKS)} заданий для Паронимов")

# Орфография (задание 1)
with open('ege_tasks_1.json', 'r', encoding='utf-8') as f:
    raw_ege_tasks_1_data = json.load(f)

bot_tasks_set_1 = []
for task_raw in raw_ege_tasks_1_data:
    q_text = task_raw['problem_text']
    raw_answer_from_json = task_raw['answer']
    ans_match = re.search(r'Ответ:\s*(\d+)', raw_answer_from_json, re.IGNORECASE)
    ans = ans_match.group(1).strip() if ans_match else ""
    if ans:
        bot_tasks_set_1.append({
            "id": task_raw['problem_number'],
            "text": escape_markdown(q_text),
            "answer": ans.lower()
        })
print(f"Загружено {len(bot_tasks_set_1)} заданий из ege_tasks_1.json")

# Ударения
try:
    with open('ege_stress_tasks.json', 'r', encoding='utf-8') as f:
        raw_stress_tasks = json.load(f)
    stress_tasks = []
    for task in raw_stress_tasks:
        stress_tasks.append({
            "id": task.get('id', task.get('number', len(stress_tasks) + 1)),
            "text": escape_markdown(task['text']),
            "answer": task['answer'].lower()
        })
    print(f"Загружено {len(stress_tasks)} заданий по Ударениям")
except Exception as e:
    print("Файл с ударениями не найден, создаём пустой список")
    stress_tasks = []

# Слитно/Раздельно (задание 13)
def ifsep(s):
    if "/C/" in s or "/С/" in s:
        return "Слитно"
    else:
        return "Раздельно"

with open('task13.txt', 'r', encoding='utf-8') as f:
    t13_tasks = []
    k = f.readline().strip()
    counter = 1
    while k != "":
        t13_tasks.append({"id": counter, "text": k.replace("/C/", "").replace("/С/", ""), "answer": ifsep(k)})
        k = f.readline().strip()
        counter += 1
print(f"Загружено {len(t13_tasks)} заданий Слитно/Раздельно")

# Общий список для случайного режима
ALL_TASKS = bot_tasks_set_1 + TASKS + t13_tasks + stress_tasks
print(f"Всего заданий для случайного режима: {len(ALL_TASKS)}")

user_ans = {}
user_streaks = {}
user_solved_tasks = {}
# Для хранения типа текущего задания (кнопочное или текстовое)
user_current_task_type = {}  # 'buttons' или 'text'

def get_correct_word_form(number, form1, form2, form3):
    if number % 100 == 11:
        return form3
    elif number % 10 == 1:
        return form1
    elif number % 100 in [12, 13, 14]:
        return form3
    elif number % 10 in [2, 3, 4]:
        return form2
    else:
        return form3

async def send_random_photo(chat_id, context):
    global available_pictures
    if not PICTURES:
        return
    if not available_pictures:
        available_pictures = list(PICTURES)
    pic = random.choice(available_pictures)
    available_pictures.remove(pic)
    try:
        with open(pic, "rb") as img:
            await context.bot.send_photo(chat_id=chat_id, photo=img)
    except Exception:
        await send_random_photo(chat_id, context)

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("Орфография", callback_data='choose_set_1')],
        [InlineKeyboardButton("Паронимы", callback_data='choose_set_2')],
        [InlineKeyboardButton("Слитно/Раздельно", callback_data='choose_set_4')],
        [InlineKeyboardButton("Ударения", callback_data='choose_set_3')],
        [InlineKeyboardButton("🎲 Случайное", callback_data='choose_random')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(
        "Привет! Это бот для подготовки к ЕГЭ по русскому языку. Выбери, чем займешься сегодня 👇",
        reply_markup=reply_markup
    )

async def show_task_types(update, context):
    keyboard = [
        [InlineKeyboardButton("Орфография", callback_data='choose_set_1')],
        [InlineKeyboardButton("Паронимы", callback_data='choose_set_2')],
        [InlineKeyboardButton("Слитно/Раздельно", callback_data='choose_set_4')],
        [InlineKeyboardButton("Ударения", callback_data='choose_set_3')],
        [InlineKeyboardButton("🎲 Случайное", callback_data='choose_random')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(
        "Выбери тип заданий, которые будем тренировать:",
        reply_markup=reply_markup
    )

async def skolko_command(update, context):
    ege = date(2026, 6, 24)
    now = datetime.now()
    n = (ege - now.date()).days
    day_word = get_correct_word_form(n, "день", "дня", "дней")
    await update.message.reply_text(f"До ЕГЭ осталось {n} {day_word}")

async def get_filtered_tasks(uid, task_list):
    if uid not in user_solved_tasks:
        return list(task_list)
    solved = user_solved_tasks[uid]
    return [t for t in task_list if t.get('id', t['text']) not in solved]

async def send_random_task(update_or_query, context, display_name=None):
    uid = update_or_query.effective_user.id
    chat_id = update_or_query.effective_chat.id

    available_tasks = context.user_data.get('available_tasks')
    if not available_tasks:
        total_solved = len(user_solved_tasks.get(uid, set()))
        total_all = len(ALL_TASKS)
        if total_solved >= total_all:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Да!", callback_data='restart_all_tasks')],
                [InlineKeyboardButton("Нет, я всё!", callback_data='tired')]
            ])
            await context.bot.send_message(chat_id=chat_id,
                text="Ничего себе! Все задания прорешаны! Начнём заново?",
                reply_markup=keyboard)
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Да!", callback_data='restart_current_type')],
                [InlineKeyboardButton("Нет, вернуться к выбору типа", callback_data='back_to_main_menu')]
            ])
            await context.bot.send_message(chat_id=chat_id,
                text="Ничего себе! Все задания этого типа прорешаны! Начнём заново?",
                reply_markup=keyboard)
        return

    context.user_data['task_counter'] = context.user_data.get('task_counter', 0) + 1
    task_display_number = context.user_data['task_counter']

    t = random.choice(available_tasks)
    available_tasks.remove(t)

    # Сохраняем данные задания
    user_ans[uid] = t['answer']
    context.user_data['current_task_text'] = t['text']
    context.user_data['current_task_answer'] = t['answer']

    # Отмечаем задание как решённое
    task_id = t.get('id', t['text'])
    if uid not in user_solved_tasks:
        user_solved_tasks[uid] = set()
    user_solved_tasks[uid].add(task_id)

    #prefix = f"Выбран тип {display_name}.\n\n" if display_name else ""
    prefix = ""
    # Определяем, показывать кнопки или текстовый ввод
    if t['answer'] in ('Слитно', 'Раздельно'):
        user_current_task_type[uid] = 'buttons'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Слитно", callback_data='answer_slitno')],
            [InlineKeyboardButton("Раздельно", callback_data='answer_razdelno')]
        ])
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{prefix}📝 *Задание {task_display_number}*\n\n{t['text']}\n\n👇 *Выберите ответ:*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        user_current_task_type[uid] = 'text'
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{prefix}📝 *Задание {task_display_number}*\n\n{t['text']}\n\n✏️ *Напиши ответ:*",
            parse_mode='Markdown'
        )

async def button_callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    chat_id = query.message.chat.id

    # Обработка выбора типа задания
    if query.data.startswith('choose_'):
        if query.data == 'choose_set_1':
            filtered_tasks = await get_filtered_tasks(uid, bot_tasks_set_1)
            context.user_data['available_tasks'] = filtered_tasks
            context.user_data['selected_task_type_key'] = 'set_1'
        elif query.data == 'choose_set_2':
            filtered_tasks = await get_filtered_tasks(uid, TASKS)
            context.user_data['available_tasks'] = filtered_tasks
            context.user_data['selected_task_type_key'] = 'set_2'
        elif query.data == 'choose_set_3':
            filtered_tasks = await get_filtered_tasks(uid, stress_tasks)
            context.user_data['available_tasks'] = filtered_tasks
            context.user_data['selected_task_type_key'] = 'set_3'
        elif query.data == 'choose_set_4':
            filtered_tasks = await get_filtered_tasks(uid, t13_tasks)
            context.user_data['available_tasks'] = filtered_tasks
            context.user_data['selected_task_type_key'] = 'set_4'
        elif query.data == 'choose_random':
            filtered_tasks = await get_filtered_tasks(uid, ALL_TASKS)
            context.user_data['available_tasks'] = filtered_tasks
            context.user_data['selected_task_type_key'] = 'random'
        context.user_data['task_counter'] = 0
        await query.message.delete()
        await send_random_task(update, context, query.data.split('_')[1].replace('set_', 'Тип ').replace('random', 'Случайный режим'))
        return

    # Обработка кнопок "Слитно"/"Раздельно"
    if query.data in ('answer_slitno', 'answer_razdelno'):
        if uid not in user_ans:
            await query.answer("Сначала выберите тип задания!", show_alert=True)
            return

        # Убираем кнопки из сообщения с заданием (но само сообщение оставляем)
        await query.message.edit_reply_markup(reply_markup=None)

        correct_answer = user_ans[uid].lower().strip()
        user_choice = "слитно" if query.data == 'answer_slitno' else "раздельно"
        current_streak = user_streaks.get(uid, 0)

        if user_choice == correct_answer:
            current_streak += 1
            user_streaks[uid] = current_streak
            await query.message.reply_text(f"✅ Правильно! Это {current_streak}-й правильный ответ подряд.")
            if current_streak > 0 and current_streak % 5 == 0:
                streak_word = get_correct_word_form(current_streak, "правильный ответ", "правильных ответа", "правильных ответов")
                await query.message.reply_text(f"🎉 Ты набрал {current_streak} {streak_word} подряд, поздравляю! 🎉")
            if uid in user_ans:
                del user_ans[uid]
            if uid in user_current_task_type:
                del user_current_task_type[uid]
            feedback_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Ещё!", callback_data='get_another_task')],
                [InlineKeyboardButton("К выбору типа", callback_data='back_to_main_menu')]
            ])
            await query.message.reply_text("Что дальше?", reply_markup=feedback_keyboard)
        else:
            broken_streak = current_streak
            user_streaks[uid] = 0
            await send_random_photo(chat_id, context)
            if broken_streak > 0:
                streak_word = get_correct_word_form(broken_streak, "правильного ответа", "правильных ответов", "правильных ответов")
                error_msg = f"❌ Неправильно. Прерван страйк из {broken_streak} {streak_word}. Можешь попробовать ещё раз!"
            else:
                error_msg = "❌ Неправильно. Можешь попробовать ещё раз!"
            incorrect_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Попытаться ещё раз!", callback_data='incorrect_try_again')],
                [InlineKeyboardButton("Показать ответ", callback_data='incorrect_show_answer')]
            ])
            await query.message.reply_text(error_msg, reply_markup=incorrect_keyboard)
        return

    # Остальные callback'ы (get_another_task, back_to_main_menu, tired, restart_* и т.д.)
    if query.data == 'get_another_task':
        if uid in user_ans:
            del user_ans[uid]
        if uid in user_current_task_type:
            del user_current_task_type[uid]
        await query.message.delete()
        await send_random_task(update, context)
    elif query.data == 'back_to_main_menu':
        if 'available_tasks' in context.user_data:
            del context.user_data['available_tasks']
        if 'selected_task_type_key' in context.user_data:
            del context.user_data['selected_task_type_key']
        context.user_data['task_counter'] = 0
        if uid in user_ans:
            del user_ans[uid]
        if uid in user_current_task_type:
            del user_current_task_type[uid]
        await query.message.delete()
        await show_task_types(update, context)
    elif query.data == 'tired':
        await query.message.delete()
        await context.bot.send_message(chat_id=chat_id, text="Ну иди отдохни. Ты молодец! 🫶")
        if uid in user_ans:
            del user_ans[uid]
        if uid in user_current_task_type:
            del user_current_task_type[uid]
    elif query.data == 'restart_all_tasks':
        if uid in user_solved_tasks:
            del user_solved_tasks[uid]
        selected_task_type_key = context.user_data.get('selected_task_type_key')
        if selected_task_type_key == 'set_1':
            context.user_data['available_tasks'] = list(bot_tasks_set_1)
            display_name = "Орфография"
        elif selected_task_type_key == 'set_2':
            context.user_data['available_tasks'] = list(TASKS)
            display_name = "Паронимы"
        elif selected_task_type_key == 'set_3':
            context.user_data['available_tasks'] = list(stress_tasks)
            display_name = "Ударения"
        elif selected_task_type_key == 'set_4':
            context.user_data['available_tasks'] = list(t13_tasks)
            display_name = "Слитно/раздельно"
        elif selected_task_type_key == 'random':
            context.user_data['available_tasks'] = list(ALL_TASKS)
            display_name = "Случайный режим"
        else:
            return
        context.user_data['task_counter'] = 0
        if uid in user_ans:
            del user_ans[uid]
        if uid in user_current_task_type:
            del user_current_task_type[uid]
        await query.message.delete()
        await context.bot.send_message(chat_id=chat_id, text=f"Начинаем заново! Выбран тип {display_name}.")
        await send_random_task(update, context, display_name)
    elif query.data == 'restart_current_type':
        selected_task_type_key = context.user_data.get('selected_task_type_key')
        if selected_task_type_key == 'set_1':
            context.user_data['available_tasks'] = list(bot_tasks_set_1)
            display_name = "Орфография"
            if uid in user_solved_tasks:
                type_ids = {t.get('id', t['text']) for t in bot_tasks_set_1}
                user_solved_tasks[uid] = user_solved_tasks[uid] - type_ids
        elif selected_task_type_key == 'set_2':
            context.user_data['available_tasks'] = list(TASKS)
            display_name = "Паронимы"
            if uid in user_solved_tasks:
                type_ids = {t.get('id', t['text']) for t in TASKS}
                user_solved_tasks[uid] = user_solved_tasks[uid] - type_ids
        elif selected_task_type_key == 'set_3':
            context.user_data['available_tasks'] = list(stress_tasks)
            display_name = "Ударения"
            if uid in user_solved_tasks:
                type_ids = {t.get('id', t['text']) for t in stress_tasks}
                user_solved_tasks[uid] = user_solved_tasks[uid] - type_ids
        elif selected_task_type_key == 'set_4':
            context.user_data['available_tasks'] = list(t13_tasks)
            display_name = "Слитно/раздельно"
            if uid in user_solved_tasks:
                type_ids = {t.get('id', t['text']) for t in t13_tasks}
                user_solved_tasks[uid] = user_solved_tasks[uid] - type_ids
        elif selected_task_type_key == 'random':
            if uid in user_solved_tasks:
                del user_solved_tasks[uid]
            context.user_data['available_tasks'] = list(ALL_TASKS)
            display_name = "Случайный режим"
        else:
            return
        context.user_data['task_counter'] = 0
        if uid in user_ans:
            del user_ans[uid]
        if uid in user_current_task_type:
            del user_current_task_type[uid]
        await query.message.delete()
        await context.bot.send_message(chat_id=chat_id, text=f"Начинаем заново! Выбран тип {display_name}.")
        await send_random_task(update, context, display_name)
    elif query.data == 'incorrect_try_again':
        current_task_text = context.user_data.get('current_task_text', "")
        current_task_answer = context.user_data.get('current_task_answer', "")
        task_display_number = context.user_data.get('task_counter', 0)
        await query.message.delete()
        if current_task_answer in ('Слитно', 'Раздельно'):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Слитно", callback_data='answer_slitno')],
                [InlineKeyboardButton("Раздельно", callback_data='answer_razdelno')]
            ])
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📝 *Задание {task_display_number}*\n\n{current_task_text}\n\n👇 *Выберите ответ:*",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            # Восстанавливаем user_ans для этого задания
            user_ans[uid] = current_task_answer
            user_current_task_type[uid] = 'buttons'
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Введи ответ на задание ещё раз:\n\n{current_task_text}\n\n✏️ *Напиши ответ:*",
                parse_mode='Markdown'
            )
            user_current_task_type[uid] = 'text'
    elif query.data == 'incorrect_show_answer':
        await query.message.delete()
        want = user_ans.get(uid)
        if want:
            await context.bot.send_message(chat_id=chat_id, text=f"Правильный ответ: *{want}*", parse_mode='Markdown')
            if uid in user_ans:
                del user_ans[uid]
            if uid in user_current_task_type:
                del user_current_task_type[uid]
            user_streaks[uid] = 0
            feedback_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Ещё!", callback_data='get_another_task')],
                [InlineKeyboardButton("К выбору типа", callback_data='back_to_main_menu')]
            ])
            await context.bot.send_message(chat_id=chat_id, text="Что дальше?", reply_markup=feedback_keyboard)

async def check(update, context):
    uid = update.effective_user.id

    # Команда "сколько?"
    if update.message.text.lower().strip() in ["сколько?", "сколько"]:
        await skolko_command(update, context)
        return

    # Если нет активного задания
    if uid not in user_ans:
        keyboard = [
            [InlineKeyboardButton("Орфография", callback_data='choose_set_1')],
            [InlineKeyboardButton("Паронимы", callback_data='choose_set_2')],
            [InlineKeyboardButton("Слитно/Раздельно", callback_data='choose_set_4')],
            [InlineKeyboardButton("Ударения", callback_data='choose_set_3')],
            [InlineKeyboardButton("🎲 Случайное", callback_data='choose_random')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Сначала выбери тип задания!", reply_markup=reply_markup)
        return

    # Если текущее задание с кнопками, но пользователь вводит текст – предупредить
    if user_current_task_type.get(uid) == 'buttons':
        await update.message.reply_text("Пожалуйста, отвечайте на это задание с помощью кнопок под сообщением.")
        return

    # Обычная текстовая проверка
    raw_user_input = update.message.text.lower().replace('ё', 'е').strip()
    want = user_ans[uid].lower().replace('ё', 'е').strip()
    if want.isdigit():
        got = raw_user_input.replace(" ", "")
    else:
        got = " ".join(raw_user_input.split())
        want = " ".join(want.split())

    current_streak = user_streaks.get(uid, 0)

    if got == want:
        current_streak += 1
        user_streaks[uid] = current_streak
        await update.message.reply_text(f"✅ Правильно! Это {current_streak}-й правильный ответ подряд.")
        if current_streak > 0 and current_streak % 5 == 0:
            streak_word_congrats = get_correct_word_form(current_streak, "правильный ответ", "правильных ответа", "правильных ответов")
            await update.message.reply_text(f"🎉 Ты набрал {current_streak} {streak_word_congrats} подряд, поздравляю! 🎉")
        if uid in user_ans:
            del user_ans[uid]
        if uid in user_current_task_type:
            del user_current_task_type[uid]
        feedback_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ещё!", callback_data='get_another_task')],
            [InlineKeyboardButton("К выбору типа", callback_data='back_to_main_menu')]
        ])
        await update.message.reply_text("Что дальше?", reply_markup=feedback_keyboard)
    else:
        broken_streak = current_streak
        user_streaks[uid] = 0
        await send_random_photo(update.effective_chat.id, context)
        if broken_streak > 0:
            streak_word = get_correct_word_form(broken_streak, "правильного ответа", "правильных ответов", "правильных ответов")
            error_message = f"❌ Неправильно. Прерван страйк из {broken_streak} {streak_word}. Можешь попробовать ещё раз!"
        else:
            error_message = "❌ Неправильно. Можешь попробовать ещё раз!"
        incorrect_feedback_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Попытаться ещё раз!", callback_data='incorrect_try_again')],
            [InlineKeyboardButton("Показать ответ", callback_data='incorrect_show_answer')]
        ])
        await update.message.reply_text(error_message, reply_markup=incorrect_feedback_keyboard)

# Запуск бота
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_callback_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check))

print("Бот запущен! Отправьте /start в Telegram")
app.run_polling(drop_pending_updates=True)
