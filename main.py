import telebot
from telebot import types
from telebot.types import InputMediaPhoto
from telebot.types import InputMediaVideo
from datetime import datetime
from datetime import timedelta
import config
import sqlite3
import time
import traceback



bot = telebot.TeleBot(config.TOKEN)



markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
item1 = types.KeyboardButton("Создать альбом")
markup.add(item1)







def delete_values(message):
	with sqlite3.connect("bot.db") as bd:
		sq = bd.cursor()
		sq.execute(f"DELETE FROM user_values WHERE user_id={message.chat.id}")



def add_new_user(message):
	with sqlite3.connect("users.db") as bd:
		sq = bd.cursor()
		sq.execute("""CREATE TABLE IF NOT EXISTS users(
			user_id INT,
			started_date DATETIME
			)""")
		sq.execute(f"SELECT user_id FROM users WHERE user_id = {message.chat.id} ")
		if sq.fetchone() is None:
			try:
				sq.execute(f"INSERT INTO users values(?,?)",(message.chat.id,datetime.now()))
			except:
				print(f"{datetime.now()}: не удалось добавить нового пользователя {message.chat.id}")

@bot.message_handler(commands=['start'])
def start_bot(message):
	add_new_user(message)
	bot.send_message(message.chat.id, "Привет! Данный бот умеет делать медиа альбомы",
					 parse_mode='html', reply_markup=markup)

@bot.message_handler(commands=['stop'])
def stop_bot(message):
	with sqlite3.connect("users.db") as bd:
		sq = bd.cursor()
		try:
			sq.execute(f"DELETE FROM users WHERE user_id = {message.chat.id}")
		except:
			print(f"{datetime.now()}: не удалось удалить пользователя {message.chat.id}")

@bot.message_handler(commands=['send']) # отправка сообщения всем пользователям (админская функция)
def send_message_to_all(message):
	with sqlite3.connect("users.db") as bd:
		sq = bd.cursor()
		sq.execute(f"SELECT admin_id FROM admins WHERE admin_id = {message.chat.id}") 
		if sq.fetchone():    # проверка прав на команду
			unsuccess_counter = 0
			success_counter = 0
			for i in sq.execute("SELECT user_id FROM users"):
				try:
					bot.send_message(i[0],message.text.split(maxsplit=1)[1])
					success_counter = success_counter + 1
				except:
					unsuccess_counter = unsuccess_counter + 1
			bot.send_message(message.chat.id,f"✅ Отправлено: {success_counter}\n❎ Не отправлено: {unsuccess_counter}")

@bot.message_handler(content_types=['text'])
def bot_handler(message):
	if message.chat.type == 'private':
		add_new_user(message)
		if message.text == 'Создать альбом':
			#bd
			with sqlite3.connect("bot.db") as bd:
				sq = bd.cursor()
				sq.execute("""CREATE TABLE IF NOT EXISTS user_values(
					user_id INT,
					file_id TEXT,
					caption TEXT,
					type TEXT
					)""")
			delete_values(message)
			bot.send_message(message.chat.id, "Хорошо! Отправьте мне медиа файлы(фото/видео), из которых нужно сделать альбом\n\n<b>При отправке альбома, бот будет добавлять первый медиа файл этого альбома</b>",
							 parse_mode='html')
			bot.register_next_step_handler(message, handler_video)
		else:
			bot.send_message(message.chat.id, "No comments...", parse_mode='html', reply_markup=markup)


def user_has_media(message):
	with sqlite3.connect("bot.db") as bd:
		sq = bd.cursor()
		sq.execute(f"SELECT * FROM user_values WHERE user_id = {message.chat.id}")
		if sq.fetchone() is None:
			return False
		else:
			return True


def handler_video(message):
	if message.chat.type == 'private':
		markup = types.InlineKeyboardMarkup(row_width=1)
		contin = types.InlineKeyboardButton("Далее", callback_data='next')
		cancel_i = types.InlineKeyboardButton("Отмена", callback_data='cancel')
		markup.add(contin,cancel_i)
		with sqlite3.connect("bot.db") as bd:
			sq = bd.cursor()
			if message.video:
				sq.execute(f"INSERT INTO user_values VALUES(?,?,?,?)",(message.chat.id,message.video.file_id,"","video"))
				bot.send_message(message.chat.id, "Отлично! Отправьте следующий медиа файл или нажмите далее", parse_mode='html',
								 reply_markup=markup)
				bot.register_next_step_handler(message, handler_video)
			elif message.photo:
				sq.execute(f"INSERT INTO user_values VALUES(?,?,?,?)",(message.chat.id,message.photo[0].file_id,"","photo"))
				bot.send_message(message.chat.id, "Отлично! Отправьте следующий медиа файл или нажмите далее", parse_mode='html',
				reply_markup=markup)
				bot.register_next_step_handler(message, handler_video)
			else:
				bot.send_message(message.chat.id, "Неверный формат файла! Необходимо отправлять медиа файлы", parse_mode='html',reply_markup=markup)
				bot.register_next_step_handler(message, handler_video)




def set_description_f(message):
	if message.chat.type == 'private':
		with sqlite3.connect("bot.db") as bd:
			sq = bd.cursor()
			sq.execute(f"UPDATE user_values SET caption = '{message.text}' WHERE ROWID = (SELECT ROWID FROM user_values WHERE user_id = {message.chat.id} LIMIT 1)")

		markup = types.InlineKeyboardMarkup(row_width=1)
		set_description = types.InlineKeyboardButton("Изменить описание альбома", callback_data='set_description')
		v_album = types.InlineKeyboardButton("Завершить", callback_data='create_videoAlbum')
		cancel_i = types.InlineKeyboardButton("Отмена", callback_data='cancel')
		markup.add(v_album,set_description,cancel_i)
		bot.send_message(message.chat.id, 'Описание успешно изменено!', reply_markup=markup)

def make_videoAlbum(message):
	media = []
	with sqlite3.connect("bot.db") as bd:
		sq = bd.cursor()
		for i in sq.execute(f"SELECT file_id,caption,type FROM user_values WHERE user_id = {message.chat.id}"):
			if(i[2] == "video"):
				media.append(InputMediaVideo(i[0]))
			elif(i[2] == "photo"):
				media.append(InputMediaPhoto(i[0]))
			else:
				print("Не добавляет :(")
		for i in sq.execute(f"SELECT caption FROM user_values WHERE user_id = {message.chat.id} LIMIT 1"):
			media[0].caption = i[0]
	bot.send_media_group(message.chat.id, media)
	media = []
	delete_values(message)



@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
	global media
	if call.message:
		if call.data == 'next':
			bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
			if not user_has_media(call.message):
				bot.send_message(call.message.chat.id, 'Необходимо отправить хотя бы один медиа файл')
				bot.register_next_step_handler(call.message, handler_video)
				bot.answer_callback_query(callback_query_id=call.id, show_alert=False,
					text="")
			else:
				markup = types.InlineKeyboardMarkup(row_width=1)
				set_description = types.InlineKeyboardButton("Изменить описание альбома", callback_data='set_description')
				v_album = types.InlineKeyboardButton("Завершить", callback_data='create_videoAlbum')
				cancel_i = types.InlineKeyboardButton("Отмена", callback_data='cancel')
				markup.add(v_album,set_description,cancel_i)
				bot.send_message(call.message.chat.id, 'Медиа файлы успешно сохранены!', reply_markup=markup)
				# remove old msg
				bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
				bot.answer_callback_query(callback_query_id=call.id, show_alert=False,
					text="")
		if call.data == 'set_description': 
			bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
			bot.send_message(call.message.chat.id, 'Введите описание:')
			bot.register_next_step_handler(call.message, set_description_f)
			bot.answer_callback_query(callback_query_id=call.id, show_alert=False,
				text="")
		if call.data == 'create_videoAlbum':
			make_videoAlbum(call.message)
			bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
			bot.answer_callback_query(callback_query_id=call.id, show_alert=False,
				text="")
		if call.data == 'cancel':
			markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
			item1 = types.KeyboardButton("Создать альбом")
			markup.add(item1)
			bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
			bot.send_message(call.message.chat.id, 'Создание альбома отменено',reply_markup=markup)
			bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
			delete_values(call.message)
			bot.answer_callback_query(callback_query_id=call.id, show_alert=False,text="")



bot.enable_save_next_step_handlers(delay=2)

bot.infinity_polling(True)
bot.polling(none_stop=True)#, timeout=123)


