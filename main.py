import os
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pathlib import Path
import pandas as pd
import psycopg2

load_dotenv(".env")
token = os.getenv("BOT_TOKEN")
db = os.getenv("DB_NAME")
db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_INTERNAL_HOST")
db_port = os.getenv("DB_PORT")

bot = telebot.TeleBot(token, parse_mode=None)


connection_params = {"database": db,
                     "user": db_username,
                     "host": db_host,
                     "password": db_password,
                     "port": db_port}


def gen_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Yes", callback_data="cb_yes"),
               InlineKeyboardButton("No", callback_data="cb_no"))
    return markup


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):

    bot.reply_to(message, f"""Hi, how are you doing {message.from_user.first_name}?
Welcome to MyPay. What would you like to do today?

This is a list of the commands:
/create_wallet - To create a wallet.
                 
/wallet_balance - To know how much you have in your wallet.
                 
/make_payment - To add money into your wallet.
                 
/purchase_history - To check your purchase history.
                 
/delete - To Delete your wallet. We are supposed to refund the money but I haven't implemented that yet.
                 
/support - For support information.""")


@bot.message_handler(commands=['create_wallet'])
def create_account(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    user_id = message.from_user.id

    select_sql = "SELECT user_id FROM user_wallet WHERE user_id = %s;"
    insert_sql = "INSERT INTO user_wallet (user_id, wallet_balance) VALUES (%s, %s);"

    cursor.execute(select_sql, (user_id,))
    result = cursor.fetchone()

    if result:
        bot.reply_to(
            message, "You already have a wallet with us silly 🙃.")
    else:
        wallet_balance = 0
        cursor.execute(insert_sql, (user_id, wallet_balance))
        bot.reply_to(
            message, "Wallet Created 👍. To add money in your wallet /make_payment")
        connection.commit()

    cursor.close()
    connection.close()


@bot.message_handler(commands=['wallet_balance'])
def wallet_balance(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    user_id = message.from_user.id

    select_sql = "SELECT wallet_balance FROM user_wallet WHERE user_id = %s;"

    cursor.execute(select_sql, (user_id,))
    result = cursor.fetchone()

    if result:
        wallet_balance = result[0]
        bot.reply_to(
            message, f'Your wallet balance is  ₦{wallet_balance}')
    else:
        bot.reply_to(
            message, "You don't have a wallet with us. To create a wallet click /create_wallet")

    cursor.close()
    connection.close()


@bot.message_handler(commands=['make_payment'])
def make_payment(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    user_id = message.from_user.id

    select_sql = "SELECT user_id FROM user_wallet WHERE user_id = %s;"

    cursor.execute(select_sql, (user_id,))
    result = cursor.fetchone()

    if result:
        bot.reply_to(
            message, f"click on this link https://paystack.com/pay/mypay8")
    else:
        bot.reply_to(
            message, "You can't make payments since you don't have a wallet. To create a wallet click /create_wallet.")

    cursor.close()
    connection.close()


@bot.message_handler(commands=['delete'])
def delete(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    user_id = message.from_user.id

    select_sql = "SELECT user_id FROM user_wallet WHERE user_id = %s;"

    cursor.execute(select_sql, (user_id,))
    result = cursor.fetchone()

    if result:
        bot.reply_to(
            message, f"Are you sure you want to delete your wallet?", reply_markup=gen_markup())
    else:
        bot.reply_to(
            message, "You can't delete a wallet since you don't have one yet. To create a wallet click /create_wallet.")

    cursor.close()
    connection.close()


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    user_id = call.from_user.id

    delete_sql = "DELETE FROM user_wallet WHERE user_id = %s;"

    if call.data == "cb_yes":
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.reply_to(call.message, "Your wallet has been deleted.😞😞")
        cursor.execute(delete_sql, (user_id,))
        connection.commit()

    elif call.data == "cb_no":
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.reply_to(call.message, "Great!!! You still have your wallet.")

    cursor.close()
    connection.close()


@bot.message_handler(commands=['support'])
def support(message):
    bot.send_message(chat_id=message.from_user.id,
                     text="contact @adebola_duf or call +2349027929326")


bot.polling()
