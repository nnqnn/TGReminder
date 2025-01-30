import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from datetime import datetime, timedelta
import config

# Настройки бота
BOT_TOKEN = config.BOT_TOKEN
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Словарь для хранения задач (chat_id: [(time, task)])
reminders = {}
user_states = {}

async def send_reminders():
    while True:
        now = datetime.now()
        for chat_id, tasks in list(reminders.items()):
            for task_time, task_text in tasks[:]:
                if now >= task_time:
                    try:
                        await bot.send_message(chat_id, f"\U0001F514 Напоминание: {task_text}")
                        tasks.remove((task_time, task_text))
                    except Exception as e:
                        logging.error(f"Ошибка отправки напоминания: {e}")
            if not tasks:
                del reminders[chat_id]
        await asyncio.sleep(10)

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.reply("Привет! Я бот-напоминалка. Чтобы создать напоминание, используйте команду /remind")

@dp.message_handler(commands=['remind'])
async def remind_command(message: types.Message):
    await message.reply("Что вам напомнить?")
    user_states[message.chat.id] = {'step': 'waiting_for_task'}

@dp.message_handler()
async def handle_messages(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_states:
        state = user_states[chat_id]
        
        if state['step'] == 'waiting_for_task':
            state['task_text'] = message.text
            state['step'] = 'waiting_for_time'
            await message.reply("Через какое время напомнить? Например: 1 час 5 минут, 2 дня 3 часа 10 минут")
        
        elif state['step'] == 'waiting_for_time':
            try:
                time_units = {"секунд": "seconds", "секунды": "seconds", "секунда": "seconds",
                              "минут": "minutes", "минуты": "minutes", "минута": "minutes",
                              "час": "hours", "часа": "hours", "часов": "hours",
                              "день": "days", "дня": "days", "дней": "days",
                              "неделя": "weeks", "недели": "weeks", "недель": "weeks",
                              "месяц": "days", "месяца": "days", "месяцев": "days",
                              "год": "days", "года": "days", "лет": "days"}
                
                time_matches = re.findall(r"(\d+)\s*(\D+)", message.text.lower())
                if not time_matches:
                    raise ValueError("Неверный формат времени")
                
                kwargs = {}
                for amount, unit in time_matches:
                    amount = int(amount)
                    unit = unit.rstrip("а").rstrip("я").strip()  # Нормализация слов
                    if unit in time_units:
                        key = time_units[unit]
                        if key in kwargs:
                            kwargs[key] += amount
                        else:
                            kwargs[key] = amount * (30 if unit.startswith("месяц") else 365 if unit.startswith("год") else 1)
                    else:
                        raise ValueError("Не удалось распознать единицу времени")
                
                reminder_time = datetime.now() + timedelta(**kwargs)
                
                if chat_id not in reminders:
                    reminders[chat_id] = []
                reminders[chat_id].append((reminder_time, state['task_text']))
                
                await message.reply(f"\U0001F4CC Запомнил! Напомню через {message.text}: {state['task_text']}")
                del user_states[chat_id]
            except Exception as e:
                await message.reply("Ошибка обработки времени. Попробуйте снова, например: 1 час 5 минут, 2 дня 3 часа 10 минут")
                logging.error(f"Ошибка обработки времени: {e}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(send_reminders())
    executor.start_polling(dp, skip_updates=True)
