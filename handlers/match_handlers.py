from misc import dp, bot
from services.db_service import db_service
from consts.db_keys import USERS_DB_KEY, MATCHES_DB_KEY, DRAGONS_DB_KEY
from consts.dragon_statuses import dragon_statuses
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.callback_data import CallbackData
from time import time

callback_accept_match = CallbackData('accept_match', 'initiator_id')
callback_decline_match = CallbackData('decline_match', 'initiator_id')

callback_new_target = CallbackData('break_match', 'new_target_username')

async def send_match(user_id, username_target):
  if has_user_match(user_id):
    user_match = db_service.get_obj_by_id(MATCHES_DB_KEY, user_id)
    target_match = db_service.get_obj_by_id(MATCHES_DB_KEY, user_match['target_id'])
    keyboard = create_is_wanna_continue_keyboard(username_target)
    await bot.send_message(user_id, f'Ваш дуэль с героем @{target_match["username"]} еще не окончен!\nЖелаете прервать текущий дуэль и сдаться?', reply_markup=keyboard)
    return
  
  user = db_service.get_obj_by_id(USERS_DB_KEY, user_id)
  if user['username'] == username_target:
    await bot.send_message(user_id, 'Вы не можете вызвать на дуэль самого себя.\nВ дуэле участвуют двое!')
    return

  users = db_service.get_db(USERS_DB_KEY)

  target_id = 0
  for id in users.keys():
    if users[id]['username'] == username_target:
      target_id = id
      break
  if not target_id:
    print('WARN: Target user is not found')
    await bot.send_message(user_id, 'Герой с таким именем не найден.\nПригласите его в игру по реферальной ссылке!\n\n/ref - Пригласить друга')
    return

  if has_user_match(target_id):
    await bot.send_message(user_id, 'Выбранный герой сейчас участвует в дуэле.')
    return

  user = db_service.get_obj_by_id(USERS_DB_KEY, user_id)
  if not await can_participate_match(user_id, user):
    return

  try:
    keyboard = create_accept_keyboard(user_id)
    await bot.send_message(
      target_id,
      f'Герой @{user["username"]} вызывает вас на дуэль!',
      reply_markup=keyboard
    )
  except:
    await bot.send_message(user_id, f'<b><i>Герой @{username_target} покинул мир Draconis. Дуэль не состоится</i></b>')
    return

  await bot.send_message(user_id, f'Герою @{username_target} отправлен вызов на дуэль!')

@dp.callback_query_handler(callback_accept_match.filter())
async def accept_match(callback: CallbackQuery):
  target_id = callback.message.chat.id
  if has_user_match(target_id):
    target_match = db_service.get_obj_by_id(MATCHES_DB_KEY, target_id)
    target_target_match = db_service.get_obj_by_id(MATCHES_DB_KEY, target_match['target_id'])
    keyboard = create_is_wanna_continue_keyboard(target_target_match['username'])
    await bot.send_message(target_id, f'Ваш дуэль с героем @{target_target_match["username"]} еще не окончен!\nЖелаете прервать текущий дуэль и сдаться', reply_markup=keyboard)
    return

  initiator_id = callback.data.split(':')[1]

  if has_user_match(initiator_id):
    await bot.send_message(target_id, 'Этот герой сейчас участвует в другом дуэле. Дуэль не состоится.')
    return

  await callback.message.delete()

  user_target = db_service.get_obj_by_id(USERS_DB_KEY, target_id)
  user_initiator = db_service.get_obj_by_id(USERS_DB_KEY, initiator_id)

  try:
    if not await can_participate_match(target_id, user_target):
      await bot.send_message(initiator_id, f'Герой @{user_target["username"]} не в состоянии принять участие. Дуэль не состоится.')
      return
    if not await can_participate_match(initiator_id, user_initiator):
      await bot.send_message(target_id, f'Герой @{user_initiator["username"]} уже не в состоянии принять участие. Дуэль не состоится.')
      return
    await bot.send_message(initiator_id, f'Герой @{user_target["username"]} принял ваш запрос на дуэль!')
    keyboard = create_choose_shelter_keyboard()
    await bot.send_message(initiator_id, f'Герой @{user_target["username"]} атакует вас первым! Выберите укрытие!', reply_markup=keyboard)
  except:
    await bot.send_message(target_id, f'<b><i>Герой @{user_target["username"]} покинул мир Draconis. Дуэль не состоится.</i></b>', parse_mode='html')
    return

  await create_match(initiator_id, user_initiator, target_id)
  await create_match(target_id, user_target, initiator_id)
  await bot.send_message(target_id, 'Вы приняли дуэль!\n<b><i>Ожидайте хода соперника!</i></b>', parse_mode='html')

@dp.callback_query_handler(callback_decline_match.filter())
async def decline_match(callback: CallbackQuery):
  initiator_id = callback.data.split(':')[1]
  await callback.message.delete()
  await bot.send_message(callback.message.chat.id, 'Вы отклонили дуэль.')
  await bot.send_message(initiator_id, 'Дуэль был отклонен.')

# ----------------------------------------------

@dp.callback_query_handler(text='continue_match')
async def continue_match(callback: CallbackQuery):
  await callback.message.delete()

@dp.callback_query_handler(callback_new_target.filter())
async def break_match(callback: CallbackQuery):
  await callback.message.delete()
  user_id = callback.message.chat.id
  user_match = db_service.get_obj_by_id(MATCHES_DB_KEY, user_id)
  winner_id = user_match['target_id']
  try:
    await bot.send_message(winner_id, f'Ваш соперник @{user_match["username"]} сдался!')
    await match_result(winner_id, user_id)
  except:
    print('ERR: Cannot break match')
  new_target_username = callback.data.split(':')[1]
  await send_match(user_id, new_target_username)

# ------------------------------------------------

@dp.callback_query_handler(text='choose_shelter_1')
async def choose_shelter_1(callback: CallbackQuery):
  await choose_shelter(callback, 1)

@dp.callback_query_handler(text='choose_shelter_2')
async def choose_shelter_2(callback: CallbackQuery):
  await choose_shelter(callback, 2)

@dp.callback_query_handler(text='choose_shelter_3')
async def choose_shelter_3(callback: CallbackQuery):
  await choose_shelter(callback, 3)

# ------------------------------------------------
@dp.callback_query_handler(text='check_shelter_1')
async def check_shelter_1(callback: CallbackQuery):
  await check_shelter(callback, 1)

@dp.callback_query_handler(text='check_shelter_2')
async def check_shelter_2(callback: CallbackQuery):
  await check_shelter(callback, 2)

@dp.callback_query_handler(text='check_shelter_3')
async def check_shelter_3(callback: CallbackQuery):
  await check_shelter(callback, 3)

async def choose_shelter(callback, shelter):
  await callback.message.delete()
  user_id = callback.message.chat.id
  user_match = db_service.get_obj_by_id(MATCHES_DB_KEY, user_id)
  update_shelter(user_match, user_id, shelter)
  await bot.send_message(user_id, 'Отличный выбор! Ожидайте хода от соперника.')

  target_id = user_match['target_id']
  keyboard = create_check_shelter_keyboard()
  try:
    await bot.send_message(target_id, 'Отыщите соперника! Он в одном из этих укрытий:', reply_markup=keyboard)
  except:
    await bot.send_message(user_id, '<b><i>Соперник покинул мир Draconis.</i></b>', parse_mode='html')
    await match_result(user_id, target_id, False)

async def check_shelter(callback, shelter):
  await callback.message.delete()
  user_id = callback.message.chat.id
  user_match = db_service.get_obj_by_id(MATCHES_DB_KEY, user_id)
  target_id = user_match['target_id']
  target_match = db_service.get_obj_by_id(MATCHES_DB_KEY, target_id)

  is_win = shelter == target_match['shelter']
  try:
    if is_win:
      user_match['wins'] = user_match['wins'] + 1
      await bot.send_message(user_id, f'Ваш огонь настиг соперника!\n\n<b>Счет:\n<i>Вы: {user_match["wins"]}\n@{target_match["username"]}: {target_match["wins"]}</i></b>', parse_mode='html')
      await bot.send_message(target_id, f'Соперник обнаружил вас и атаковал!\n\n<b>Счет:\n<i>Вы: {target_match["wins"]}\n@{user_match["username"]}: {user_match["wins"]}</i></b>', parse_mode='html')
    else:
      await bot.send_message(target_id, f'Соперник вас не обнаружил!\n\n<b>Счет:\n<i>Вы: {target_match["wins"]}\n@{user_match["username"]}: {user_match["wins"]}</i></b>', parse_mode='html')
      await bot.send_message(user_id, f'Соперник не обнаружен.\n\n<b>Счет:\n<i>Вы: {user_match["wins"]}\n@{target_match["username"]}: {target_match["wins"]}</i></b>', parse_mode='html')
  except:
    await bot.send_message(user_id, '<b><i>Этот герой покинул мир Draconis.</i></b>', parse_mode='html')
    await match_result(user_id, target_id, False)
    return

  user_match['updated_at'] = time() * 1000
  db_service.set_obj_by_id(MATCHES_DB_KEY, user_id, user_match)

  target_match['shelter'] = 0
  target_match['updated_at'] = time() * 1000
  db_service.set_obj_by_id(MATCHES_DB_KEY, target_id, target_match)

  if user_match['wins'] > 1:
    await match_result(user_id, target_id)
    return
  if target_match['wins'] > 1:
    await match_result(target_id, user_id)
    return

  await bot.send_message(target_id, '<b><i>Ожидайте хода соперника.</i></b>', parse_mode='html')
  keyboard = create_choose_shelter_keyboard()
  await bot.send_message(user_id, f'Соперник @{target_match["username"]} перешел в атаку! Выберите укрытие!', reply_markup=keyboard)

async def match_result(winner_id, loser_id, is_loser_in_game=True):
  db_service.set_obj_by_id(MATCHES_DB_KEY, winner_id, {})
  db_service.set_obj_by_id(MATCHES_DB_KEY, loser_id, {})

  winner = db_service.get_obj_by_id(USERS_DB_KEY, winner_id)
  winner['dracoins'] = winner['dracoins'] + 200
  db_service.set_obj_by_id(USERS_DB_KEY, winner_id, winner)
  await bot.send_message(winner_id, '<b>Вы одержали победу!</b>\nВы свергли своего соперника!\nДуэль завершен.\n\n<b>+200 дракоинов!</b>\n\n/dragons - Мои драконы\n/dracoins - Дракоины', parse_mode='html')
  if is_loser_in_game:
    await bot.send_message(loser_id, '<b>Вы потерпели поражение!</b>\nВаш соперник одержал верх.\nДуэль завершен.\n\n/dragons - Мои драконы', parse_mode='html')

async def can_participate_match(user_id, user):
  if user['dracoins'] < 100:
    await bot.send_message(user_id, 'Недостаточно дракоинов!\nНеобходимо 100 дракоинов за участие дуэле.\n\n/dracoins - Дракоины')
    return False
  dragons = None
  try:
    dragons = user['dragons']
  except:
    await bot.send_message(user_id, 'У вас нет драконов!\nДля участия в дуэле необходим хотя бы один дракон.\n\n/eggs - Драконьи яйца')
    return False
  has_old_alive_dragon = False
  for dragon_id in dragons:
    dragon = db_service.get_obj_by_id(DRAGONS_DB_KEY, dragon_id)
    if dragon['status'] == dragon_statuses[1] and dragon['height'] >= 100:
      has_old_alive_dragon = True
  if not has_old_alive_dragon:
    await bot.send_message(user_id, 'Для участия в дуэле у вас должен быть хотя бы один здоровый дракон ростом не менее 10 см.\n\n/dragons - Мои драконы')

  return has_old_alive_dragon

async def create_match(user_id, user, target_id):
  user['dracoins'] = user['dracoins'] - 100
  db_service.set_obj_by_id(USERS_DB_KEY, user_id, user)

  await bot.send_message(user_id, '<b>Удержано 100 дракоинов.</b>', parse_mode='html')

  match = { 'username': user['username'] }
  match['target_id'] = target_id
  match['updated_at'] = time() * 1000
  match['wins'] = 0
  match['shelter'] = 0
  db_service.set_obj_by_id(MATCHES_DB_KEY, user_id, match)
  return True

def create_accept_keyboard(initiator_id):
  keyboard = InlineKeyboardMarkup()
  keyboard.add(InlineKeyboardButton(
    text='Принять дуэль',
    callback_data=callback_accept_match.new(str(initiator_id)))
  )
  keyboard.add(InlineKeyboardButton(
    text='Отклонить',
    callback_data=callback_decline_match.new(str(initiator_id)))
  )
  return keyboard

def create_is_wanna_continue_keyboard(new_target_username):
  keyboard = InlineKeyboardMarkup()
  keyboard.add(InlineKeyboardButton(
    text='Продолжить текуший дуэль',
    callback_data='continue_match'
  ))
  keyboard.add(InlineKeyboardButton(
    text='Сдаться',
    callback_data=callback_new_target.new(new_target_username),
  ))
  return keyboard

def has_user_match(user_id):
  return db_service.is_obj_exists(MATCHES_DB_KEY, user_id)

def create_choose_shelter_keyboard():
  keyboard = InlineKeyboardMarkup()
  keyboard.add(InlineKeyboardButton(
    text='🪨 🪨🪨 🪨',
    callback_data='choose_shelter_1'
  ))
  keyboard.add(InlineKeyboardButton(
    text='🪨🪨🪨 🪨🪨',
    callback_data='choose_shelter_2'
  ))
  keyboard.add(InlineKeyboardButton(
    text='🪨🪨🪨🪨 🪨',
    callback_data='choose_shelter_3'
  ))
  return keyboard

def create_check_shelter_keyboard():
  keyboard = InlineKeyboardMarkup()
  keyboard.add(InlineKeyboardButton(
    text='🌳🌳 🌳 🌳',
    callback_data='check_shelter_1'
  ))
  keyboard.add(InlineKeyboardButton(
    text='🌳 🌳🌳 🌳',
    callback_data='check_shelter_2'
  ))
  keyboard.add(InlineKeyboardButton(
    text='🌳🌳 🌳🌳🌳',
    callback_data='check_shelter_3'
  ))
  return keyboard

def update_shelter(user_match, user_id, shelter):
  user_match['shelter'] = shelter
  user_match['updated_at'] = time() * 1000
  db_service.set_obj_by_id(MATCHES_DB_KEY, user_id, user_match)
