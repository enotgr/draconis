import asyncio
from datetime import datetime, timedelta
from services.db_service import db_service
from consts.db_keys import USERS_DB_KEY
from misc import bot

event_hours = 13

def get_delta():
  now = datetime.now()
  next_time = now

  hours = datetime.now().time().hour
  hours_delta = hours
  if hours < event_hours:
    hours_delta = event_hours - hours_delta
    next_time += timedelta(hours=hours_delta)
  else:
    hours_delta = hours_delta - event_hours
    next_time = next_time + timedelta(days=1) - timedelta(hours=hours_delta)
  minutes_delta = datetime.now().time().minute
  seconds_delta = datetime.now().time().second
  next_time = next_time - timedelta(minutes=minutes_delta) - timedelta(seconds=seconds_delta)
  return next_time.timestamp() - now.timestamp()

async def send_message(user_id, text):
  try:
    await bot.send_message(user_id, text, parse_mode='html')
  except:
    # TODO: Удалять данные этих пользователей из базы
    print(f'ERR: Bot was blocked by user. User ID: {user_id}')

async def add_dracoins(user_id, user):
  dracoins = user['dracoins'] + 100
  user['dracoins'] = dracoins
  await send_message(user_id, '<i>Вам начислено 100 дракоинов!</i>\nВ кошельке <b>{0}</b> дракоинов!\n\n/dracoins - Дракоины\n/dragons - Мои драконы'.format(dracoins))

async def tick():
  while True:
    delta = get_delta()
    print('timer:', format_time(delta))
    await asyncio.sleep(1)

async def init_time_service():
  while True:
    delta = get_delta()
    print('timer:', format_time(delta))
    await asyncio.sleep(delta)
    users = db_service.get_db(USERS_DB_KEY)

    for user_id in users.keys():
      user = users[user_id]
      await add_dracoins(user_id, user)
    db_service.save_db(USERS_DB_KEY, users)

def format_time(seconds):
  sec = seconds % (24 * 3600)
  hour = sec // 3600
  sec %= 3600
  min = sec // 60
  sec %= 60
  return '%02d:%02d:%02d' % (hour, min, sec)