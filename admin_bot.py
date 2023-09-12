import telebot
import psycopg2
import os
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv(".env")
token = os.getenv("ADMIN_BOT_TOKEN")
db = os.getenv("DB_NAME")
db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_EXTERNAL_HOST")
db_port = os.getenv("DB_PORT")
admin_password = os.getenv("ADMIN_PASSWORD")

connection_params = {"database": db,
                     "user": db_username,
                     "host": db_host,
                     "password": db_password,
                     "port": db_port}

bot = telebot.TeleBot(token, parse_mode=None)
userglobal_id = 1
password = None
updated_wallets = []


def gen_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Add", callback_data="cb_add"),
               InlineKeyboardButton("Deduct", callback_data="cb_deduct"))
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Hi Adebola. I hope you are doing great.")
    bot.send_message(
        message.chat.id, "To continue, click on /password")
    # bot.send_message(
    #     message.chat.id, "To update the wallet balance of any user click /enter_user_id")


@bot.message_handler(commands=['password'])
def password(message):
    msg = bot.send_message(message.chat.id, "Enter your password Adebola")
    bot.register_next_step_handler(msg, password_enter)


def password_enter(message):
    global password
    password = message.text
    if password == admin_password:
        bot.reply_to(message,
                     text=f"Authorised ✅. You can now go on to do other stuffs.")
        bot.delete_message(message.chat.id, message.message_id)
    else:
        bot.reply_to(
            message, "Authentication Failed. click on /password for another chance. Don't worry you have unlimited trials and trust me you won't get it 🤗")


@bot.message_handler(commands=['enter_user_id'])
def handle_enter_name(message):
    global password
    if password == admin_password:
        msg = bot.reply_to(message, "Please enter the user's id:")

        bot.register_next_step_handler(msg, process_user_id)
    else:
        bot.reply_to(
            message, "You are not authorised. Click /password for authentication.")


def process_user_id(message):
    global userglobal_id
    userglobal_id = int(message.text)

    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()
    select_sql = "SELECT user_id FROM user_wallet WHERE user_id = %s;"

    cursor.execute(select_sql, (userglobal_id,))
    result = cursor.fetchone()

    if result:  # to verify if i actually inputed a correct user_id
        bot.reply_to(
            message, f"user id {userglobal_id} is valid. Do you want to:", reply_markup=gen_markup())
    else:
        bot.reply_to(
            message, f"user_id {userglobal_id} doesn't exist.")

    cursor.close()
    connection.close()


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):

    if call.data == "cb_add":
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        msg = bot.send_message(
            call.message.chat.id, f"How much do you want to add to {userglobal_id}'s account?")
        bot.register_next_step_handler(msg, add_to_wallet)

    elif call.data == "cb_deduct":
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        msg = bot.send_message(
            call.message.chat.id, f"How much do you want to deduct from {userglobal_id}'s account?")
        bot.register_next_step_handler(msg, deduct_from_wallet)


def add_to_wallet(message):
    amount = float(message.text)
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    update_sql = "UPDATE user_wallet SET wallet_balance = wallet_balance + %s WHERE user_id = %s;"
    cursor.execute(update_sql, (amount, userglobal_id))

    connection.commit()
    cursor.close()
    connection.close()
    bot.send_message(
        message.chat.id, f"You have added ₦{amount} to {userglobal_id}'s wallet. Click /done if you are done for today.")
    updated_wallets.append(str(userglobal_id))


def deduct_from_wallet(message):
    amount = float(message.text)
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    update_sql = "UPDATE user_wallet SET wallet_balance = wallet_balance - %s WHERE user_id = %s;"
    cursor.execute(update_sql, (amount, userglobal_id))

    connection.commit()
    cursor.close()
    connection.close()

    bot.send_message(
        message.chat.id, f"You have deducted ₦{amount} from {userglobal_id}'s wallet. Click /done if you are done for today.")
    updated_wallets.append(str(userglobal_id))


@bot.message_handler(commands=['done'])
def done(message):
    global userglobal_id, password, updated_wallets

    if password == admin_password:
        updated_wallets = set(updated_wallets)
        bot.reply_to(
            message, f"You have updated user id {', '.join(set(updated_wallets))} wallets. Keep the grind up Adebola. Goal=🦄")
        userglobal_id = 1
        password = None
        updated_wallets = []
    else:
        bot.reply_to(
            message, "You are not authorised. Click /password for authentication.")


bot.polling()
