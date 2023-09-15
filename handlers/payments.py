from misc import dp, bot
# from utils.handler_utils import send
from services import db_service
from consts.db_keys import USERS_DB_KEY, PAYMENTS_DB_KEY
from consts.payment_consts import config, dracoins_by_cost, payment_statuses
from consts.admins import admins
# from payment_token import PAYMENT_TOKEN
from aiogram import types
# from aiogram.types.message import ContentType
from aiogram.utils.callback_data import CallbackData
from yookassa import Payment, Configuration
import asyncio
import uuid
import time

Configuration.account_id = config['account_id']
Configuration.secret_key = config['secret_key']

call_back_info = CallbackData('status', 'payment_id')

@dp.callback_query_handler(call_back_info.filter())
async def status(callback: types.CallbackQuery):
  payment_id = callback.data.split(':')[1]
  payment = Payment.find_one(payment_id)
  payment_db = db_service.get_obj_by_id(PAYMENTS_DB_KEY, payment_id)
  if payment_db['status'] == payment_statuses[2]:
    await send_success(callback.message.chat.id, payment)
    return

  text = 'Информация о покупке:\n\n'
  if payment.status == payment_statuses[0]:
    text += 'Платеж создан и ожидает действий от вас.\nНажмите кнопку "Оплатить" для оплаты.'
  elif payment.status == payment_statuses[1]:
    text += 'Покупка оплачена, деньги авторизованы и ожидают списания.'
  elif payment.status == payment_statuses[2]:
    user = db_service.get_obj_by_id(USERS_DB_KEY, callback.message.chat.id)
    user['dracoins'] = user['dracoins'] + dracoins_by_cost[str(payment.amount.value)]
    db_service.set_obj_by_id(USERS_DB_KEY, callback.message.chat.id, user)
    text += f'Платеж на сумму {str(payment.amount.value)} {str(payment.amount.currency)} успешно завершен.\n'
    text += f'Вам начислено {dracoins_by_cost[str(payment.amount.value)]} дракоинов!'
    await send_success_admin(callback.message.chat.id, user['username'], payment_id, payment)
  elif payment.status == payment_statuses[3]:
    text += 'Платеж отменен.'
  else:
    text += 'Что-то пошло не так. Поробуйте проверить позже'
    user = db_service.get_obj_by_id(USERS_DB_KEY, callback.message.chat.id)
    await send_problem_admin(callback.message.chat.id, user['username'], payment_id, payment)

  payment_db['status'] = payment.status
  db_service.set_obj_by_id(PAYMENTS_DB_KEY, payment_id, payment_db)
  await bot.send_message(callback.message.chat.id, text)

@dp.callback_query_handler(text='500')
async def buy_500_dracoins(callback: types.CallbackQuery):
  await callback.message.delete()
  await send_invoice(callback.message, 500, 50)

@dp.callback_query_handler(text='1100')
async def buy_1100_dracoins(callback: types.CallbackQuery):
  await callback.message.delete()
  await send_invoice(callback.message, 1100, 100)

@dp.callback_query_handler(text='2300')
async def buy_2300_dracoins(callback: types.CallbackQuery):
  await callback.message.delete()
  await send_invoice(callback.message, 2300, 200)

@dp.callback_query_handler(text='5900')
async def buy_5900_dracoins(callback: types.CallbackQuery):
  await callback.message.delete()
  await send_invoice(callback.message, 5900, 500)

@dp.message_handler(commands=['donate'])
async def donate(message: types.Message):
  # if message.from_user.id not in admins:
  #   await send(message, 'В ближайшее время донаты станут доступны, но не сейчас ;(\nМы сообщим, когда эта возможность появится.')
  #   return

  # photo = types.InputFile('images/draconis.png')
  # await bot.send_photo(chat_id=message.from_user.id, photo=photo)

  keyboard = create_keyboard()
  await message.answer(
    'Выберите количество дракоинов:',
    reply_markup=keyboard
  )

async def send_invoice(message, dracoins, amount):
  payment = create_payment(amount, dracoins)

  payment_db = { 'status': payment.status }
  payment_db['amount'] = str(payment.amount.value)
  payment_db['user_id'] = message.chat.id
  payment_db['created_at'] = time.time() * 1000
  db_service.set_obj_by_id(PAYMENTS_DB_KEY, payment.id, payment_db)

  keyboard = types.InlineKeyboardMarkup()
  keyboard.add(types.InlineKeyboardButton(
    text='Оплатить 💳',
    url=payment.confirmation.confirmation_url)
  )
  keyboard.add(types.InlineKeyboardButton(
    text='Проверить статус платежа',
    callback_data=call_back_info.new(payment_id=payment.id))
  )
  await message.answer(
    f'Чтобы оплатить покупку {dracoins} дракоинов, нажмите кнопку "Оплатить":',
    reply_markup=keyboard
  )
  await check_payment(message.chat.id, payment.id)

async def check_payment(user_id, payment_id):
  payment = Payment.find_one(payment_id)
  i = 0
  while payment.status == payment_statuses[0] or payment.status == payment_statuses[1]:
    i = i + 1
    payment = Payment.find_one(payment_id)
    await asyncio.sleep(5)

    if i == 180:
      break

  payment_db = db_service.get_obj_by_id(PAYMENTS_DB_KEY, payment_id)
  if payment_db['status'] == payment_statuses[2]:
    print('Уже начислено.')
    return

  if payment.status == payment_statuses[2]:
    user = db_service.get_obj_by_id(USERS_DB_KEY, user_id)
    user['dracoins'] = user['dracoins'] + dracoins_by_cost[str(payment.amount.value)]
    db_service.set_obj_by_id(USERS_DB_KEY, user_id, user)
    await send_success(user_id, payment)
    await send_success_admin(user_id, user['username'], payment_id, payment)
  else:
    print('BAD RETURN')

  payment_db = db_service.get_obj_by_id(PAYMENTS_DB_KEY, payment_id)
  payment_db['status'] = payment.status
  db_service.set_obj_by_id(PAYMENTS_DB_KEY, payment_id, payment_db)

def create_payment(amount, dracoins):
  idempotence_key = str(uuid.uuid4())
  return Payment.create({
    'amount': {
      'value': f'{amount}.00',
      'currency': 'RUB'
    },
    "capture": True,
    'payment_method_data': {
      'type': 'bank_card'
    },
    'confirmation': {
      'type': 'redirect',
      'return_url': 'https://t.me/draconis_game_bot'
    },
    'description': f'Покупка {dracoins} дракоинов'
  }, idempotence_key)

def create_keyboard():
  keyboard = types.InlineKeyboardMarkup()
  keyboard.add(types.InlineKeyboardButton(
    text='500 дракоинов [50 RUB]',
    callback_data='500')
  )
  keyboard.add(types.InlineKeyboardButton(
    text='1100 дракоинов [100 RUB]',
    callback_data='1100')
  )
  keyboard.add(types.InlineKeyboardButton(
    text='2300 дракоинов [200 RUB]',
    callback_data='2300')
  )
  keyboard.add(types.InlineKeyboardButton(
    text='5900 дракоинов [500 RUB]',
    callback_data='5900')
  )
  return keyboard

async def send_success(user_id, payment):
  text = f'Платеж на сумму {str(payment.amount.value)} {str(payment.amount.currency)} успешно завершен.\n'
  text += f'Вам начислено {dracoins_by_cost[str(payment.amount.value)]} дракоинов!'
  await bot.send_message(user_id, text)

async def send_success_admin(user_id, username, payment_id, payment):
  text = 'Успешная транзакция:\n'
  text += f'\nuser_id: {user_id}'
  text += f'\nusername: @{username}'
  text += f'\npayment_id: {payment_id}'
  text += f'\namount: {str(payment.amount.value)} {str(payment.amount.currency)}'
  await bot.send_message(admins[0], text)

async def send_problem_admin(user_id, username, payment_id, payment):
  text = 'Проблемы с оплатой:\n'
  text += f'\nuser_id: {user_id}'
  text += f'\nusername: @{username}'
  text += f'\npayment_id: {payment_id}'
  text += f'\npayment_status: {payment.status}'
  await bot.send_message(admins[0], text)

# Этот код пригодится, когда платёжная система будет готова
# pre checkout  (must be answered in 10 seconds)
# @dp.pre_checkout_query_handler(lambda query: True)
# async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
#   await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

# # successful payment
# @dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
# async def successful_payment(message: types.Message):
#   print('SUCCESSFUL PAYMENT:')
#   payment_info = message.successful_payment.to_python()
#   for k, v in payment_info.items():
#     print(f'{k} = {v}')

#   purchased_dracoins = dracoins_by_cost[message.successful_payment.total_amount]
#   user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
#   user['dracoins'] = user['dracoins'] + purchased_dracoins
#   db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)

#   await bot.send_message(message.from_user.id,
#                         f'Платеж на сумму {message.successful_payment.total_amount // 100} {message.successful_payment.currency} прошел успешно!\nЗачислено {purchased_dracoins} дракоинов!\n\n/dracoins - Дракоины')

# async def send_invoice(user_id, dracoins):
#   PRICE = calculate_price(dracoins)
#   await bot.send_invoice(user_id,
#                          title='Покупка дракоинов',
#                          description=f'Покупка {dracoins} дракоинов',
#                          provider_token=PAYMENT_TOKEN,
#                          currency='rub',
#                          photo_url='https://i.postimg.cc/hGrRBf3R/2023-01-17-18-11-44.png',
#                          photo_width=1814,
#                          photo_height=810,
#                          photo_size=98374,
#                          is_flexible=False,
#                          prices=[PRICE],
#                          start_parameter='purchase-of-game-currency',
#                          payload='real-invoice-live')

# def calculate_price(dracoins_amount):
#   amount = dracoins_prices[dracoins_amount]
#   return types.LabeledPrice(label=f'Купить {dracoins_amount} дракоинов', amount=amount)
