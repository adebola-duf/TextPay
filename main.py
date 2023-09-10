import os
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pathlib import Path
import pandas as pd

load_dotenv(".env")
token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(token, parse_mode=None)


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
    user_data = pd.read_excel('user_data.xlsx')
    user_id = message.from_user.id

    if user_id in user_data['User_ID'].values:
        bot.reply_to(
            message, "You already have a wallet with us silly 🙃.")

    else:
        user_data = pd.concat([user_data, pd.DataFrame(
            {'User_ID': [user_id], 'Wallet_Balance': [0]})])
        bot.reply_to(
            message, "Wallet Created 👍. To add money in your wallet /make_payment")

        user_data.to_excel('user_data.xlsx', index=False)


@bot.message_handler(commands=['wallet_balance'])
def wallet_balance(message):

    user_data = pd.read_excel('user_data.xlsx')
    user_id = message.from_user.id

    if user_id in user_data['User_ID'].values:
        bot.reply_to(
            message, f'Your wallet balance is  ₦{user_data.loc[user_data["User_ID"] == user_id]["Wallet_Balance"].values.item()}')

    else:
        bot.reply_to(
            message, "You don't have a wallet with us. To create a wallet click /create_wallet")


@bot.message_handler(commands=['make_payment'])
def make_payment(message):
    user_data = pd.read_excel('user_data.xlsx')
    user_id = message.from_user.id

    if user_id in user_data['User_ID'].values:
        bot.reply_to(
            message, f"click on this link https://paystack.com/pay/mypay-demo")

    else:
        bot.reply_to(
            message, "You can't make payments since you don't have a wallet. To create a wallet click /create_wallet.")


@bot.message_handler(commands=['delete'])
def delete(message):

    user_data = pd.read_excel('user_data.xlsx')
    user_id = message.from_user.id

    if user_id in user_data['User_ID'].values:
        bot.reply_to(
            message, f"Are you sure you want to delete your wallet?", reply_markup=gen_markup())

    else:
        bot.reply_to(
            message, "You can't delete a wallet since you don't have one yet. To create a wallet click /create_wallet.")


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):

    user_data = pd.read_excel('user_data.xlsx')
    user_id = call.from_user.id

    if call.data == "cb_yes":
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.reply_to(call.message,
                     "Your wallet has been deleted.😞😞")
        user_data.drop(user_data[user_data['User_ID']
                       == user_id].index, inplace=True)
        user_data.to_excel('user_data.xlsx', index=False)

    elif call.data == "cb_no":
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.reply_to(
            call.message, "Great!!! You still have your wallet.")


@bot.message_handler(commands=['support'])
def support(message):
    bot.send_message(chat_id=message.from_user.id,
                     text="contact @adebola_duf or call +2349027929326")


bot.polling()
