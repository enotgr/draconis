from handlers import main_handlers
from services.time_service import init_time_service, tick
from misc import dp, set_menu
from aiogram import executor
import asyncio

async def on_startup(x):
  tasks = [
    init_time_service(),
    set_menu(),
    # tick()
  ]
  asyncio.gather(*tasks)

if __name__ == '__main__':
  executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
