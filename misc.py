from bot_token import TOKEN # token is hidden, contact the author
from aiogram import Bot, Dispatcher, types

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

async def set_menu():
  await dp.bot.set_my_commands([
    types.BotCommand('/dragons', 'Драконы'),
    types.BotCommand('/leaderboard', 'Лидерборд'),
    types.BotCommand('/dracoins', 'Дракоины'),
    types.BotCommand('/market', 'Таверна'),
    types.BotCommand('/ref', 'Пригласить друга'),
    types.BotCommand('/eggs', 'Яйца'),
  ])
