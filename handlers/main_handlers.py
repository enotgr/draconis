from misc import bot, dp
from services.db_service import db_service
from utils.handler_utils import send
from consts.db_keys import USERS_DB_KEY, DRAGONS_DB_KEY
from consts.admins import admins
from consts.dragon_types import dragon_types, dragon_types_titles
from consts.dragon_genuses import dragon_genuses, dragon_genuses_titles
from consts.dragon_sex import dragon_sex, dragons_sex_titles
from consts.dragon_statuses import dragon_statuses, dragon_statuses_titles
from aiogram.utils.deep_linking import get_start_link
from aiogram.types import InputFile
from random import randint
import time

egg_price = 1000

@dp.message_handler(commands=['start'])
async def send_welcome(message):
  unique_code = extract_unique_code(message.text)
  user_info = message.from_user
  id = user_info.id
  username = user_info.username
  first_name = user_info.first_name
  name = first_name if first_name else username

  if not add_user_to_db(id, username):
    await send(message, 'Ну, привет, {0}.'.format(name))
    return

  if unique_code:
    await add_referal_egg(unique_code, username)

  await send(message, '<i><b>Странник:</b>\n- Приветствую, <b>{0}</b>!\nТы проделал длинный путь, чтобы найти меня. За это я дарю тебе свое яйцо.</i>'.format(name))
  await send(message, 'Ваш инвентарь был пополнен.\n\n/eggs - Проверить яйца')

@dp.message_handler(commands=['ref'])
async def ref(message):
  link = await get_start_link(message.from_user.id)
  await send(message, f'{link}\n\nСкопируй эту ссылку и отправь другу.\nЗа каждого приведённого друга ты получишь по дополнительному яйцу!')

@dp.message_handler(commands=['image'])
async def img(message):
  photo = InputFile('images/draconis.png')
  await bot.send_photo(chat_id=message.from_user.id, photo=photo)

@dp.message_handler(commands=['eggs'])
async def eggs(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
  eggs = user['eggs']

  text = 'Драконьи яйца: {0} шт.'.format(eggs)
  if eggs > 0:
    text += '\n\n/burn - Бросить яйцо в огонь'

  await send(message, text)

@dp.message_handler(commands=['burn'])
async def burn(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
  eggs_count = user['eggs']
  if eggs_count < 1:
    await send(message, 'У вас нет яиц.\n\n/market - Таверна')
    return
  
  dragons = []

  try:
    dragons = user['dragons']
  except:
    print('ERR: Dragons are not exist')

  if len(dragons) > 6:
    await send(message, 'Вы не можете разместить в вашей пещере более 7 драконов.\n\n/dragons - Мои драконы')
    return

  user['eggs'] = user['eggs'] - 1
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)
  burn_dragon(message.from_user.id)

  await send(message, 'Вы слышите треск яйца. Похоже, у вас родился дракон!\n\n/dragons - Мои драконы'.format(eggs))

@dp.message_handler(commands=['dragons'])
async def dragons(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)

  dragons = []

  try:
    dragons = user['dragons']
  except:
    print('ERR: Dragons are not exist')

  if not len(dragons):
    await send(message, 'У вас нет драконов.\n\n/eggs - Драконьи яйца')
    return

  text = 'Драконы:\n'
  i = 0
  for id in dragons:
    dragon = db_service.get_obj_by_id(DRAGONS_DB_KEY, id)
    dragon_name = dragon['name'] if dragon['name'] else get_dragon_genus_title(dragon['type'], dragon['genus'])
    i += 1
    text += '\n/dragon_{0} - {1}'.format(i, dragon_name)
    if dragon['status'] == dragon_statuses[3]:
      text += ' <b>[Мертв]</b>'

  await send(message, text)

@dp.message_handler(commands=['dragon_1', 'dragon_2', 'dragon_3', 'dragon_4', 'dragon_5', 'dragon_6', 'dragon_7'])
async def dragon_index(message):
  dragon_number = int(message.text.split('_')[1])
  dragon_index = dragon_number - 1
  if dragon_index < 0:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)

  dragons = []
  try:
    dragons = user['dragons']
  except:
    print('ERR: Dragons are not exist')

  if len(dragons) - 1 < dragon_index:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  dragon_id = dragons[dragon_index]
  dragon = db_service.get_obj_by_id(DRAGONS_DB_KEY, dragon_id)
  dragon_name = dragon['name']

  type_title = dragon_types_titles[dragon['type']]
  genus_title = get_dragon_genus_title(dragon['type'], dragon['genus'])
  status_title = dragon_statuses_titles[dragon['status']]
  sex_title = dragons_sex_titles[dragon['sex']]

  text = dragon_name if dragon_name else genus_title
  text += ':\n\nТип: {0}'.format(type_title)
  text += '\nРод: {0}'.format(genus_title)
  text += '\nСтатус: {0}'.format(status_title)
  text += '\nПол: {0}'.format(sex_title)
  text += '\nРост: {0} см'.format(dragon['height'])

  text += '\n\n/fight_dragon_{0} - Отправить дракона в бой\n/feed_dragon_{0} - Кормить [100 дракоинов]\n/dracoins - Проверить кошелек'.format(dragon_number)

  if not dragon['name']:
    text += '\n/name_dragon_{0} ИМЯ - Дать имя дракону'.format(dragon_number)

  if dragon['status'] == dragon_statuses[3]:
    text += '\n\n/rip_dragon_{0} - Сжечь дракона'.format(dragon_number)

  await send(message, text)

@dp.message_handler(commands=['name_dragon_1', 'name_dragon_2', 'name_dragon_3', 'name_dragon_4', 'name_dragon_5', 'name_dragon_6', 'name_dragon_7'])
async def set_dragon_name(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)

  dragon_number = int(message.text.split('_')[2].split(' ')[0])
  dragon_index = dragon_number - 1
  if dragon_index < 0:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  dragons = []
  try:
    dragons = user['dragons']
  except:
    print('ERR: Dragons are not exist')

  if len(dragons) - 1 < dragon_index:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  dragon_id = dragons[dragon_index]
  dragon = db_service.get_obj_by_id(DRAGONS_DB_KEY, dragon_id)

  if dragon['name']:
    await send(message, 'У этого дракона уже есть имя. Его зовут {0}'.format(dragon['name']))
    return

  input_words = message.text.split(' ')[1:]
  new_name = ' '.join(input_words)
  if not new_name:
    await send(message, 'Вы не указали имя дракона. Боги не поняли вас.\nЧтобы дать имя дракону, необходимо написать сначала команду и через пробел имя.\nНапример, /name_dragon_{0} Мракокрад.'.format(dragon_number))
    return

  max_len = 16
  if len(new_name) > max_len:
    await send(message, f'Придумайте более короткое имя, не превышающее {max_len} символов.')
    return

  dragon['name'] = new_name
  db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, dragon)
  await send(message, 'Отлично!\nБоги приняли это имя. Они вообще всякое принимают.\nТеперь этого дракона зовут {0}!\n\n/dragon_{1}'.format(new_name, dragon_number))

@dp.message_handler(commands=['fight_dragon_1', 'fight_dragon_2', 'fight_dragon_3', 'fight_dragon_4', 'fight_dragon_5', 'fight_dragon_6', 'fight_dragon_7'])
async def fight(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)

  dragon_number = int(message.text.split('_')[2])
  dragon_index = dragon_number - 1
  if dragon_index < 0:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  dragons = []
  try:
    dragons = user['dragons']
  except:
    print('ERR: Dragons are not exist')

  if len(dragons) - 1 < dragon_index:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  dragon_id = dragons[dragon_index]
  dragon = db_service.get_obj_by_id(DRAGONS_DB_KEY, dragon_id)
  dragon_name = dragon['name'] if dragon['name'] else get_dragon_genus_title(dragon['type'], dragon['genus'])

  if dragon['status'] == dragon_statuses[3]:
    await send(message, '{0} мертв. Он не может драться. Он уже ничего не может...\n\n/rip_dragon_{1} - Сжечь дракона\n/dragons - Мои драконы'.format(dragon_name, dragon_number))
    return

  fight_result = randint(0, 1)

  text = ''
  if fight_result == 0:
    text += '{0} проиграл.\n'.format(dragon_name)
    if dragon['status'] == dragon_statuses[1]:
      dragon['status'] = dragon_statuses[2]
      text += 'Он получил травму, и теперь он ранен. Чтобы вылечить, его необходимо покормить.\n\n<i>Если снова отправить этого дракона в бой, он может погибнуть.</i>\n\n/dragon_{0} - {1}\n/feed_dragon_{0} - Кормить\n/dragons - Мои драконы'.format(dragon_number, dragon_name)
      await send(message, text)
    elif dragon['status'] == dragon_statuses[2]:
      dragon['status'] = dragon_statuses[3]
      text += 'Более того, твой дракон доблестно погиб в бою. Очень жаль, хороший был парень.\n\n/dragons - Мои драконы'
      await send(message, text)
    db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, dragon)
    return
  text += '{0} вернулся с победой!\n'.format(dragon_name)
  earnings = randint(50, 150)
  user['dracoins'] = user['dracoins'] + earnings
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)
  text += '{0} принес с собой {1} дракоинов!\n\n/dracoins - Кошелек\n/dragons - Мои драконы\n/market - Таверна'.format(dragon_name, earnings)
  await send(message, text)

@dp.message_handler(commands=['feed_dragon_1', 'feed_dragon_2', 'feed_dragon_3', 'feed_dragon_4', 'feed_dragon_5', 'feed_dragon_6', 'feed_dragon_7'])
async def feed(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
  dracoins = user['dracoins']

  dragon_number = int(message.text.split('_')[2])
  dragon_index = dragon_number - 1
  if dragon_index < 0:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  dragons = []
  try:
    dragons = user['dragons']
  except:
    print('ERR: Dragons are not exist')

  if len(dragons) - 1 < dragon_index:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  dragon_id = dragons[dragon_index]
  dragon = db_service.get_obj_by_id(DRAGONS_DB_KEY, dragon_id)

  if dragon['status'] == dragon_statuses[3]:
    await send(message, 'Этот дракон не может есть, так как он мертв.\n\n/rip_dragon_{0} - Сжечь дракона'.format(dragon_number))
    return
  
  if dracoins < 100:
    await send(message, 'У вас не достаточно средств. Корм для дракона стоит 100 дракоинов.\nСледующее пополнение будет завтра!\n\n/dracoins - Проверить кошелек.\n/donate - Купить дракоины')
    return
  
  if dragon['status'] == dragon_statuses[2]:
    dragon['status'] = dragon_statuses[1]
    await send(message, '<i>Дракон вылечился и уже чувствует себя гораздо лучше!</i>')

  grow = randint(1, 10)
  dragon['height'] = dragon['height'] + grow
  dragon['feed_at'] = time.time() * 1000
  db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, dragon)

  dracoins -= 100
  user['dracoins'] = dracoins
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)

  genus_title = get_dragon_genus_title(dragon['type'], dragon['genus'])
  dragon_name = dragon['name'] if dragon['name'] else genus_title
  await send(message, '<i>Потрачено <b>100</b> дракоинов.\nОстаток: {0}</i>\n\n/dracoins - Проверить кошелек'.format(user['dracoins']))
  await send(message, '{0} вырос на {1} см!\n\n/dragon_{2} - {3}\n/leaderboard - Топ лидеров'.format(dragon_name, grow, dragon_number, dragon_name))

@dp.message_handler(commands=['rip_dragon_1', 'rip_dragon_2', 'rip_dragon_3', 'rip_dragon_4', 'rip_dragon_5', 'rip_dragon_6', 'rip_dragon_7'])
async def rip(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)

  dragon_number = int(message.text.split('_')[2])
  dragon_index = dragon_number - 1
  if dragon_index < 0:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  dragons = []
  try:
    dragons = user['dragons']
  except:
    print('ERR: Dragons are not exist')

  if len(dragons) - 1 < dragon_index:
    await send(message, 'Такого дракона у вас нет.\n\n/dragons - Мои драконы')
    return

  dragon_id = dragons[dragon_index]
  dragon = db_service.get_obj_by_id(DRAGONS_DB_KEY, dragon_id)

  if dragon['status'] != dragon_statuses[3]:
    await send(message, 'Этот дракон еще жив. Скорее он сожжет вас, чем вы его!')
    return

  dragons.remove(dragon_id)
  user['dragons'] = dragons
  
  db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, {})
  dragon_name = dragon['name'] if dragon['name'] else get_dragon_genus_title(dragon['type'], dragon['genus'])

  text = '{0} отправился в бескрайнее путешествие. На земле этой грешной его уже никто не увидит.\n'.format(dragon_name)

  if len(dragons) == 0 and user['eggs'] == 0:
    user['eggs'] = 1
    text += '\nВ огне вы находите драконье яйцо!\n\n/eggs - Драконьи яйца'
  text += '\n/dragons - Мои драконы'
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)
  await send(message, text)

@dp.message_handler(commands=['leaderboard'])
async def leaderboard(message):
  dragons_leaders = db_service.get_leaderboard(10)
  dragon_ids = [key for key in dragons_leaders]
  dragon_ids.reverse()
  text = '🐉 Топ лидирующих драконов:\n'
  index = 0
  for id in dragon_ids:
    dragon = dragons_leaders[id]
    if dragon['status'] == dragon_statuses[3]:
      continue
    index += 1
    owner = db_service.get_obj_by_id(USERS_DB_KEY, dragon['owner'])
    username = owner['username']
    dragon_genus_title = get_dragon_genus_title(dragon['type'], dragon['genus'])
    dragon_height = dragon['height']
    text += '\n{3}. @{0} - <b>{1}</b> ({2} см)'.format(username, dragon_genus_title, dragon_height, index)
  await send(message, text)

@dp.message_handler(commands=['dracoins'])
async def dracoins(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
  await send(message, 'Дракоины: {0}'.format(user['dracoins']))

@dp.message_handler(commands=['market'])
async def market(message):
  await send(message, 'Таверна:\n\n/buy_egg - Купить яйцо [{0} дракоинов]\n/donate - Купить дракоины'.format(egg_price))

@dp.message_handler(commands=['buy_egg'])
async def buy_egg(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
  dracoins = user['dracoins']
  if dracoins < egg_price:
    await send(message, 'У вас не достаточно средств. Яйцо дракона стоит {0} дракоинов.\n\n/dracoins - Проверить кошелек.\n/donate - Купить дракоины'.format(egg_price))
    return
  user['eggs'] = user['eggs'] + 1
  user['dracoins'] = dracoins - egg_price
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)
  await send(message, 'Поздравляю!\nТы приобрел яйцо!\n\n/eggs - Проверить яйца')

@dp.message_handler()
async def public_message(message):
  if message.from_user.id not in admins:
    await bot.send_message(admins[0], 'Message from <b>@{0} [{1}]</b>: {2}'.format(message.from_user.username, message.from_user.id, message.text), parse_mode='html')
  else:
    users = db_service.get_db(USERS_DB_KEY)
    for id in users.keys():
      await bot.send_message(id, message.text, parse_mode='html')

def add_user_to_db(id, username):
  if db_service.is_obj_exists(USERS_DB_KEY, id):
    print('WARN: User is already exists')
    return False
  
  new_user = { 'username': username }
  new_user['created_at'] = time.time() * 1000
  new_user['dracoins'] = 100
  new_user['eggs'] = 1

  db_service.set_obj_by_id(USERS_DB_KEY, id, new_user)
  return True

def burn_dragon(user_id):
  dragon_id = str(user_id) + str(int(time.time()))

  new_dragon = { 'name': '' }
  dragon_type = dragon_types[randint(0, len(dragon_types) - 1)]
  new_dragon['type'] = dragon_type
  dragon_genus = dragon_genuses[dragon_type]
  new_dragon['genus'] = dragon_genus[randint(0, len(dragon_genus) - 1)]
  new_dragon['status'] = dragon_statuses[1]
  new_dragon['sex'] = dragon_sex[randint(0, 1)]
  new_dragon['height'] = randint(3, 10)
  new_dragon['owner'] = user_id
  new_dragon['created_at'] = time.time() * 1000
  new_dragon['feed_at'] = time.time() * 1000

  db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, new_dragon)

  user = db_service.get_obj_by_id(USERS_DB_KEY, user_id)

  dragons = []
  try:
    dragons = user['dragons']
  except:
    print('WARN: Array dragons was not exist')

  dragons.append(dragon_id)
  user['dragons'] = dragons
  db_service.set_obj_by_id(USERS_DB_KEY, user_id, user)

  return dragon_id

def get_dragon_genus_title(type, genus):
  return dragon_genuses_titles[type][genus]

def extract_unique_code(text):
  return text.split()[1] if len(text.split()) > 1 else None

async def add_referal_egg(unique_code, username):
  user = None
  try:
    user = db_service.get_obj_by_id(USERS_DB_KEY, unique_code)
  except:
    print(f'ERR: Incorrect referal link {unique_code}')
    return

  user['eggs'] = user['eggs'] + 1
  db_service.set_obj_by_id(USERS_DB_KEY, unique_code, user)
  await bot.send_message(unique_code, f'Ваш друг <b>{username}</b> зарегистрировался по вашей реферальной ссылке и принёс вам дополнительное яйцо!\n\n/eggs - Драконьи яйца', parse_mode='html')
