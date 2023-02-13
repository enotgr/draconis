from misc import bot, dp
from services.db_service import db_service
from services.file_service import file_service
from services.time_service import get_delta
from utils.handler_utils import send
from consts.db_keys import USERS_DB_KEY, DRAGONS_DB_KEY, PRINCESS_DB_KEY
from consts.admins import admins
from consts.dragon_types import dragon_types, dragon_types_titles
from consts.dragon_genuses import dragon_genuses, dragon_genuses_titles
from consts.dragon_sex import dragon_sex, dragons_sex_titles
from consts.dragon_statuses import dragon_statuses, dragon_statuses_titles
from consts.common import start_words, egg_price
from handlers.match_handlers import send_match
from aiogram.utils.deep_linking import get_start_link
from aiogram.utils.exceptions import BotBlocked
from aiogram.types import InputFile, Update
from asyncio import sleep
from random import randint
import qrcode
import time

@dp.message_handler(commands=['start'])
async def send_welcome(message):
  unique_code = extract_unique_code(message.text)
  user_info = message.from_user
  id = user_info.id
  username = user_info.username
  first_name = user_info.first_name
  name = first_name if first_name else username

  if not username:
    username = name
  if not username:
    heroes_count = int(file_service.getTextFileByPath('texts/unknown_heroes_count.txt')) + 1
    file_service.saveTextFile(str(heroes_count), 'texts/unknown_heroes_count.txt')
    username = f'unknown_hero_{heroes_count}_draconis'
    name = f'unknown_hero_{heroes_count}_draconis'

  if not add_user_to_db(id, username):
    await send(message, 'Ну, привет, {0}.'.format(name))
    return

  if unique_code:
    await add_referal_egg(unique_code, name)

  await send(message, '<i><b>Странник:</b>\n- Приветствую, <b>{0}</b>!\nТы проделал длинный путь, чтобы найти меня. За это я дарю тебе свое яйцо.</i>'.format(name))
  await send(message, 'Ваш инвентарь был пополнен.\n\n/eggs - Проверить яйца\n/rules - Правила игры')

@dp.message_handler(commands=['rules', 'help', 'info'])
async def rules(message):
  rules = file_service.getTextFileByPath('texts/rules.txt')
  if not rules:
    print('ERR: Invalid rules file')
    return
  await send(message, rules)

@dp.message_handler(commands=['match_rules'])
async def match_rules(message):
  rules = file_service.getTextFileByPath('texts/about_matches.txt')
  if not rules:
    print('ERR: Invalid rules file')
    return
  await send(message, rules)

@dp.message_handler(commands=['ref', 'qrcore', 'qr', 'ref_link'])
async def ref(message):
  link = await get_start_link(message.from_user.id)
  img = qrcode.make(link)
  img.save('qr_temp.jpg')
  await send(message, f'Реферальная ссылка:\n{link}')
  await bot.send_photo(message.chat.id, photo=open('qr_temp.jpg', 'rb'))
  await send(message, 'Просто отправьте ссылку другу или покажите ему qrcode!\nЗа каждого приведённого друга вы получите по яйцу!')

@dp.message_handler(commands=['image'])
async def img(message):
  await bot.send_chat_action(message.from_user.id, 'upload_photo')
  await sleep(1)
  photo = InputFile('images/draconis.png')
  await bot.send_photo(chat_id=message.from_user.id, photo=photo)

@dp.message_handler(commands=['dice'])
async def dice(message):
  response = await bot.send_dice(message.from_user.id)
  result = response['dice']['value']
  await sleep(3)
  await bot.send_message(message.from_user.id, f'Результат броска: {result}')
  return result

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
  days = int((time.time() * 1000 - dragon['created_at']) // 1000 // 60 // 24)
  age = '{0} {1}'.format(days, define_suffix(days, ['день', 'дня', 'дней']))

  text = dragon_name if dragon_name else genus_title
  text += ':\n\nТип: {0}'.format(type_title)
  text += '\nРод: {0}'.format(genus_title)
  text += '\nСтатус: {0}'.format(status_title)
  text += '\nВозраст: {0}'.format(age)
  text += '\nПол: {0}'.format(sex_title)
  text += '\nРост: {0} см'.format(dragon['height'])

  text += '\n\n/fight_dragon_{0} - Отправить в бой\n/feed_dragon_{0} - Кормить [100 дракоинов]'.format(dragon_number)

  if not dragon['name']:
    text += '\n/name_dragon_{0} ИМЯ - Дать имя дракону'.format(dragon_number)

  if dragon['status'] == dragon_statuses[3]:
    text += '\n\n/rip_dragon_{0} - Сжечь дракона [150 дракоинов]'.format(dragon_number)

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
    await send(message, 'Вы не указали имя дракона. Боги не поняли вас.\nЧтобы дать имя дракону, необходимо написать сначала команду и через пробел имя.\nНапример, /name_dragon_{0} Мракокрад.\n\n<i>Имейте ввиду: после того, как вы дадите имя дракону, его нельзя будет изменить.</i>'.format(dragon_number))
    return

  max_len = 16
  if len(new_name) > max_len:
    await send(message, f'Придумайте более короткое имя, не превышающее {max_len} символов.')
    return

  dragon['name'] = new_name
  db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, dragon)
  await send(message, 'Отлично!\nБоги приняли это имя. Они вообще всякое принимают.\nТеперь этого дракона зовут {0}!\n\n/dragon_{1} - {0}'.format(new_name, dragon_number))

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

  fight_result = await dice(message)

  princess = db_service.get_db(PRINCESS_DB_KEY)
  if not princess:
    print('ERR: Princess was not exist')
    princess = get_default_princess()
    db_service.save_db(PRINCESS_DB_KEY, princess)

  win_value = 4
  if princess['owner_id'] == message.from_user.id:
    win_value = 3

  text = ''
  if fight_result < win_value:
    text += '{0} проиграл.\n'.format(dragon_name)
    if dragon['status'] == dragon_statuses[1]:
      dragon['status'] = dragon_statuses[2]
      text += 'Он получил травму и теперь он ранен. Чтобы вылечить, его необходимо покормить.\n\n<i>Если снова отправить этого дракона в бой, он может погибнуть.</i>\n\n/dragon_{0} - {1}\n/feed_dragon_{0} - Кормить [100 дракоинов]\n/dragons - Мои драконы'.format(dragon_number, dragon_name)
      await send(message, text)
    elif dragon['status'] == dragon_statuses[2]:
      dragon['status'] = dragon_statuses[3]
      text += 'Более того, ваш дракон доблестно погиб в бою. Очень жаль, хороший был дракон.\n\n/dragons - Мои драконы'
      await send(message, text)
    db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, dragon)
    return
  text += '{0} вернулся с победой!\n'.format(dragon_name)
  earnings = randint(50, 150)
  user['dracoins'] = user['dracoins'] + earnings
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)
  text += '{0} принес с собой {1}!\n\n/fight_dragon_{2} - Отправить в бой\n/dragon_{2} - {0}\n/dragons - Мои драконы'.format(dragon_name, get_dracoins_text(earnings), dragon_number)
  await send(message, text)

  princess_random = randint(0, 100)
  print(f'INFO: @{user["username"]} is trying luck. Received value:', princess_random)
  if princess_random != 77:
    return

  old_owner_id = princess['owner_id']
  if message.from_user.id == old_owner_id:
    # TODO: можно добавить дополнительный успех в виде дракоинов или даже яйца
    return

  if old_owner_id != 0:
    loss_text = '<b>Принцесса исчезла!</b>\nПринцесса, которая когда-то была под вашим крылом, теперь исчезла, оставив вас с тяжелым сердцем. Она была захвачена другим игроком и теперь вне вашей досягаемости.\n\n'
    loss_text += '<b>-1 к удаче.</b>\nУдача покинула вас. Теперь, если при броске кости выпадет число меньше <b>4</b>, ваш дракон будет побежден.'
    await bot.send_message(old_owner_id, loss_text, parse_mode='html')

  set_princess(message.from_user.id, user['username'])
  text_princess = '<b>Принцесса с вами!</b>\nДракон вернулся с поля битвы не только с сокровищами, но и с прекрасной принцессой, которая теперь под вашим крылом!\n\n'
  text_princess += '<b>+1 удаче!</b>\nТеперь, если при броске кости выпадет <b>3</b>, <b>4</b>, <b>5</b> или <b>6</b>, дракон вернётся с победой!\n\n/princess - Где принцесса?'
  await send(message, text_princess)

@dp.message_handler(commands=['feed_dragon_1', 'feed_dragon_2', 'feed_dragon_3', 'feed_dragon_4', 'feed_dragon_5', 'feed_dragon_6', 'feed_dragon_7'])
async def feed(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
  dracoins = user['dracoins']

  top_up = 'сегодня'
  if get_delta() // 3600 > 11:
    top_up = 'завтра'

  if dracoins < 100:
    await send(message, f'У вас не достаточно монет.\nКорм для дракона стоит <b>100</b> дракоинов.\nСледующее пополнение будет {top_up}!\n\n/dracoins - Проверить кошелек.\n/donate - Купить дракоины')
    return

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
  
  dracoins -= 100
  user['dracoins'] = dracoins
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)
  await send(message, '<i>Потрачено <b>100</b> дракоинов.\nОстаток: {0}</i>'.format(get_dracoins_text(user['dracoins'])))

  dragon['feed_at'] = time.time() * 1000
  dragon_name = dragon['name'] if dragon['name'] else get_dragon_genus_title(dragon['type'], dragon['genus'])

  if dragon['status'] == dragon_statuses[2]:
    dragon['status'] = dragon_statuses[1]
    db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, dragon)
    await send(message, '<i>Дракон вылечился и уже чувствует себя гораздо лучше!</i>\n\n/fight_dragon_{0} - Отправить в бой\n/dragon_{0} - {1}'.format(dragon_number, dragon_name))
    return

  grow = randint(1, 10)
  dragon['height'] = dragon['height'] + grow
  db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, dragon)

  await send(message, '{0} вырос на <b>{1}</b> см!\n\n/dragon_{2} - {3}\n/leaderboard - Топ лидеров'.format(dragon_name, grow, dragon_number, dragon_name))

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
  
  top_up = 'сегодня'
  if get_delta() // 3600 > 11:
    top_up = 'завтра'
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
  if user['dracoins'] < 150:
    await send(message, f'У вас не достаточно монет.\nЦеремония сожжения обойдётся вам в 150 дракоинов.\nСледующее пополнение будет {top_up}!\n\n/dracoins - Проверить кошелек.\n/donate - Купить дракоины')
    return

  user['dracoins'] = user['dracoins'] - 150
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)

  dragons.remove(dragon_id)
  user['dragons'] = dragons
  
  db_service.set_obj_by_id(DRAGONS_DB_KEY, dragon_id, {})
  dragon_name = dragon['name'] if dragon['name'] else get_dragon_genus_title(dragon['type'], dragon['genus'])

  text = '{0} отправился в последнее путешествие. Его тело залилось огненной краской, ветер рассеял его пепел в воздухе. Прощай, {0}.\n'.format(dragon_name)

  if len(dragons) == 0 and user['eggs'] == 0:
    user['eggs'] = 1
    text += '\nВ огне вы находите драконье яйцо!\n\n/burn - Бросить яйцо в огонь\n/eggs - Драконьи яйца'
  text += '\n/dragons - Мои драконы'
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)
  await send(message, text)

@dp.message_handler(commands=['leaderboard'])
async def leaderboard(message):
  await bot.send_chat_action(message.from_user.id, 'typing')
  dragons_leaders = db_service.get_leaderboard(30)
  dragon_ids = [key for key in dragons_leaders]
  dragon_ids.reverse()
  text = '🐉 Топ лидирующих драконов:\n'
  index = 0
  for id in dragon_ids:
    dragon = dragons_leaders[id]
    if dragon['status'] == dragon_statuses[3]:
      continue
    index += 1
    if index > 10:
      break
    owner = db_service.get_obj_by_id(USERS_DB_KEY, dragon['owner'])
    dragon_genus_title = get_dragon_genus_title(dragon['type'], dragon['genus'])
    dragon_height = dragon['height']
    text += '\n<b>{3}.</b>{4} @{0} - <b>{1}</b> ({2} см)'.format(owner['username'], dragon_genus_title, dragon_height, index, get_leaderboard_place(index))
  await send(message, text)

@dp.message_handler(commands=['princess'])
async def princess(message):
  princess = db_service.get_db(PRINCESS_DB_KEY)
  if princess['owner_id'] == 0:
    await send(message, 'Принцесса всё ещё не найдена!')
    return

  days = int((time.time() * 1000 - princess['updated_at']) // 1000 // 60 // 24)
  long_ago = '{0} {1}'.format(days, define_suffix(days, ['день', 'дня', 'дней']))

  if message.from_user.id == princess['owner_id']:
    await send(message, f'Нежная и прекрасная принцесса уже <b>{long_ago}</b> находится в ваших умелых руках и приносит дополнительную удачу!')
    return

  username = princess['owner_username']
  await send(message, f'Нежная и прекрасная принцесса уже <b>{long_ago}</b> находится в умелых руках @{username}, принося с собой дополнительную удачу!\nОднако, каждый день драконы всех мастей стараются её заполучить в бою, ведь эта возможность есть у каждого, в том числе и у вас.\n\nОтправьте своего дракона в бой и испытайте свою удачу!\n\n/dragons - Мои драконы')

@dp.message_handler(commands=['dracoins'])
async def dracoins(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
  await send(message, 'Кошелек:\n{0}'.format(get_dracoins_text(user['dracoins'])))

@dp.message_handler(commands=['market'])
async def market(message):
  await send(message, 'Таверна:\n\n/buy_egg - Купить яйцо [{0} дракоинов]\n/donate - Купить дракоины'.format(egg_price))

@dp.message_handler(commands=['buy_egg'])
async def buy_egg(message):
  user = db_service.get_obj_by_id(USERS_DB_KEY, message.from_user.id)
  dracoins = user['dracoins']
  if dracoins < egg_price:
    await send(message, 'У вас не достаточно монет. Яйцо дракона стоит {0} дракоинов.\n\n/dracoins - Проверить кошелек.\n/donate - Купить дракоины'.format(egg_price))
    return
  user['eggs'] = user['eggs'] + 1
  user['dracoins'] = dracoins - egg_price
  db_service.set_obj_by_id(USERS_DB_KEY, message.from_user.id, user)
  await send(message, 'Поздравляю!\nТы приобрел яйцо!\n\n/eggs - Проверить яйца')

@dp.errors_handler(exception=BotBlocked)
async def bot_blocked_handler(update: Update, exception: BotBlocked):
  print('EXCEPTION: Bot was blocked by user')
  print('update:', update)
  print('exception:', exception)
  return True

@dp.message_handler()
async def other_messages(message):
  if is_some_words_in_text(start_words, message.text):
    await send_welcome(message)
    return

  if message.text[:1] == '@':
    await send_match(message.from_user.id, message.text[1:])
    return

  if message.from_user.id not in admins:
    await bot.send_message(admins[0], 'Message from <b>@{0} [{1}]</b>: {2}'.format(message.from_user.username, message.from_user.id, message.text), parse_mode='html')
  else:
    users = db_service.get_db(USERS_DB_KEY)
    for id in users.keys():
      try:
        await bot.send_message(id, message.text, parse_mode='html')
      except:
        # TODO: Удалять данные этих пользователей из базы
        print(f'ERROR: Bot was blocked by user or something went wrong. User ID: {id}')
        print(f'USERNAME:' f'{users[id]["username"]}')

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
    print('WARN: Array dragons were not exist')

  dragons.append(dragon_id)
  user['dragons'] = dragons
  db_service.set_obj_by_id(USERS_DB_KEY, user_id, user)

  return dragon_id

def get_dragon_genus_title(type, genus):
  return dragon_genuses_titles[type][genus]

def extract_unique_code(text):
  return text.split()[1] if len(text.split()) > 1 else None

async def add_referal_egg(unique_code, name):
  user = None
  try:
    user = db_service.get_obj_by_id(USERS_DB_KEY, unique_code)
  except:
    print(f'ERR: Incorrect referal link {unique_code}')
    return

  user['eggs'] = user['eggs'] + 1
  db_service.set_obj_by_id(USERS_DB_KEY, unique_code, user)
  await bot.send_message(unique_code, f'Ваш друг <b>{name}</b> зарегистрировался по вашей реферальной ссылке и принёс вам дополнительное яйцо!\n\n/eggs - Драконьи яйца', parse_mode='html')

def define_suffix(value, suffixes):
  if len(suffixes) != 3:
    return ''
  rest_of_100 = value % 100
  if rest_of_100 > 10 and rest_of_100 < 20:
    return suffixes[2]

  rest = value % 10
  if rest == 1:
    return suffixes[0]
  if rest > 1 and rest < 5:
    return suffixes[1]
  return suffixes[2]

def get_dracoins_text(dracoins):
  return '{0} {1}'.format(dracoins, define_suffix(dracoins, ['дракоин', 'дракоина', 'дракоинов']))

def get_default_princess():
  princess = { 'owner_id': 0 }
  princess['owner_username'] = ''
  princess['updated_at'] = time.time() * 1000
  return princess

def set_princess(user_id, user_name):
  princess = { 'owner_id': user_id }
  princess['owner_username'] = user_name
  princess['updated_at'] = time.time() * 1000
  db_service.save_db(PRINCESS_DB_KEY, princess)
  return princess

def is_some_words_in_text(words, text):
  for word in words:
    if word in text.lower():
      return True
  return False

def get_leaderboard_place(index):
  if index == 1:
    return ' 🥇'
  if index == 2:
    return ' 🥈'
  if index == 3:
    return ' 🥉'
  return ''
