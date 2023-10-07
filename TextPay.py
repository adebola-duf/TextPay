import os
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup  # states
from telebot import custom_filters
import psycopg2
import datetime
from decimal import Decimal, InvalidOperation
import qrcode
import io
import random
import qrcode
from fastapi import FastAPI, HTTPException, status, Request, BackgroundTasks
import uvicorn
from pydantic import BaseModel
import hashlib
import hmac
import requests
from starlette.responses import JSONResponse

# states storage
state_storage = StateMemoryStorage()  # you can init here another storage

load_dotenv(".env")
textpaybot_token = os.getenv("TEXT_PAY_BOT_TOKEN")
notifybot_token = os.getenv("NOTIFY_BOT_TOKEN")
db = os.getenv("DB_NAME")
db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_INTERNAL_HOST")
db_port = os.getenv("DB_PORT")
secret = bytes(os.getenv("PAYSTACK_SECRET_KEY"), 'UTF-8')

WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL_BASE")

bot = telebot.TeleBot(textpaybot_token, state_storage=state_storage)
notify_bot = telebot.TeleBot(notifybot_token)

connection_params = {"database": db,
                     "user": db_username,
                     "host": db_host,
                     "password": db_password,
                     "port": db_port}
# States group.

app = FastAPI()


@app.post(path=f"/{textpaybot_token}")
def process_webhook_text_pay_bot(update: dict):
    """
    Process webhook calls for textpay
    """
    if update:
        update = telebot.types.Update.de_json(update)
        bot.process_new_updates([update])
    else:
        return


class MyStates(StatesGroup):
    # Each attribute in the class represents a different state: first_name, last_name
    first_name = State()
    last_name = State()
    password = State()
    registration_info_given = State()
    # i know some of these variable names are wack but like i've got no better thing
    user_wanna_delete = State()
    delete_confirmation = State()
    password_for_delete = State()
    password_for_text_to_other = State()
    receiver_id_for_text_to_other = State()
    actual_send_to_other_state = State()
    # this is the state for when you want to create a qr
    enter_amount_to_charge_for_create_qr_state = State()

    # this is the state for when you want to scan a qr
    qr_scanned = State()
    qr_text_confirmation = State()
    password_for_qr_scan = State()

    liquidate_enter_password = State()
    liquidate_enter_amount_to_liquidate = State()
    liquidate_enter_account_number = State()
    liquidate_enter_bank_name = State()


def delete_confirmation_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Yes ✅", callback_data="cb_delete_confirmation_yes"),
               InlineKeyboardButton("No 🚫", callback_data="cb_delete_confirmation_no"))
    return markup


def name_confirmation_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Yes ✅", callback_data="cb_name_confirmation_yes"),
               InlineKeyboardButton("No 🚫", callback_data="cb_name_confirmation_no"))
    return markup


# you are meant to maybe create an account for this company so that like the charges would be going to that account so at the end of the maybe month, you'd know how much you actually have as revenue

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.from_user.username:
        bot.reply_to(message, f"""Hello 👋 @{message.from_user.username}
Welcome to TextPay. What would you like to do today?
This is a list of the commands:
/create_wallet - To create a wallet.
                
/wallet_balance - To know how much you have in your wallet.
                
/make_payment - To add money into your wallet.
                
/text_to_other - To text money to another user.
                     
/create_payment_qr - Generate a QR code for accepting payments.
                     
/scan_payment_qr - To scan a QR code for making payment.
                
/transaction_history - To see your last 10 transaction history.
                     
/cancel - To cancel any thing you are doing.
                
/purchase_history - To check your purchase history.    

/get_my_id - To get your id.     
                
/delete - To Delete your wallet.
                     
/liquidate - To liquidate money into your bank account.
                
/support - For support information.""")
    else:
        bot.reply_to(message, f"""Hello 👋
Welcome to TextPay. What would you like to do today?
This is a list of the commands:
/create_wallet - To create a wallet.
                
/wallet_balance - To know how much you have in your wallet.
                
/make_payment - To add money into your wallet.
                
/text_to_other - To text money to another user.
                     
/create_payment_qr - Generate a QR code for accepting payments.
                     
/scan_payment_qr - To scan a QR code for making payment.
                     
/transaction_history - To see your last 10 transaction history.
                     
/cancel - To cancel any thing you are doing.
                
/purchase_history - To check your purchase history.
                     
/get_my_id - To get your id.
                
/delete - To Delete your wallet. We are supposed to refund the money but I haven't implemented that yet.
                
/support - For support information.""")


@bot.message_handler(commands=['create_wallet'])
def create_account(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    user_id = message.from_user.id

    select_user_wallet_balance_sql = "SELECT wallet_balance FROM users_wallet WHERE user_id = %s;"

    cursor.execute(select_user_wallet_balance_sql, (user_id,))
    result = cursor.fetchone()

    if result:
        bot.reply_to(
            message, "You already have a wallet with us silly 🙃.")
    else:
        bot.reply_to(
            message, "Great, we just need some information to do that for you. If that's ok by you, click on /continue.")


@bot.message_handler(commands=['continue'])
def xontinue(message):
    user_id = message.from_user.id
    # implement it in such a way that only if you have an account can you click the continue
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    select_user_id_from_users_wallet_table_sql = "SELECT user_id from users_wallet WHERE user_id = %s;"
    cursor.execute(select_user_id_from_users_wallet_table_sql,
                   (user_id, ))
    result = cursor.fetchone()
    if result:
        return
    bot.send_message(
        message.from_user.id, "Please enter your first name.")
    bot.set_state(user_id=user_id, state=MyStates.first_name,
                  chat_id=message.chat.id)

    cursor.close()
    connection.close()


@bot.message_handler(state="*", commands=['cancel'])
def cancel(message):
    bot.delete_state(user_id=message.from_user.id, chat_id=message.chat.id)
    bot.reply_to(message, "cancelled.")


@bot.message_handler(state=MyStates.first_name)
def first_name(user_first_name_message):
    user_id = user_first_name_message.from_user.id
    with bot.retrieve_data(user_id=user_id, chat_id=user_first_name_message.chat.id) as user_data:
        user_data['first_name'] = user_first_name_message.text
        user_data["username"] = user_first_name_message.from_user.username
    bot.set_state(user_id=user_id, state=MyStates.last_name,
                  chat_id=user_first_name_message.chat.id)
    bot.send_message(user_first_name_message.chat.id,
                     f"Nice name you have 😊. {user_data['first_name']} please enter your last name.")


@bot.message_handler(state=MyStates.last_name)
def last_name(user_last_name_message):
    with bot.retrieve_data(user_last_name_message.from_user.id) as user_data:
        user_data["last_name"] = user_last_name_message.text
    bot.set_state(user_id=user_last_name_message.from_user.id,
                  state=MyStates.password, chat_id=user_last_name_message.chat.id)
    bot.send_message(user_last_name_message.chat.id,
                     f"One more thing. Enter a password for transactions (and remember it!) 🔒 because your text will be deleted immediately after you enter it. If forgotten, 📞 support. 😊")


@bot.message_handler(state=MyStates.password)
def password(user_password_message):
    with bot.retrieve_data(user_password_message.from_user.id, user_password_message.chat.id) as user_data:
        user_data["password"] = user_password_message.text
    bot.delete_message(user_password_message.chat.id,
                       message_id=user_password_message.message_id)
    bot.set_state(user_password_message.from_user.id, state=MyStates.registration_info_given,
                  chat_id=user_password_message.chat.id)
    bot.send_message(user_password_message.chat.id,
                     f"Just to confirm, your name is {user_data['first_name']} {user_data['last_name']} and your password is {'*' * len(user_data['password'])}", reply_markup=name_confirmation_markup())


# this message handler is for when we ask the user if they are sure that the infor they provided is correct. If when we ask them, they don't
# click the button and they go and be typing instead of clicking yes or no, we just keep asking them.
@bot.message_handler(state=MyStates.registration_info_given)
def confirmation_message(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as user_data:
        user_first_name, user_last_name, user_password = user_data[
            'first_name'], user_data["last_name"], user_data["password"]
    bot.send_message(message.chat.id,
                     f"Just to confirm, your name is {user_first_name} {user_last_name} and your password is {'*' * len(user_password)}", reply_markup=name_confirmation_markup())


@bot.callback_query_handler(state=[MyStates.registration_info_given], func=lambda call: call.data.startswith("cb_name"))
def callback_query(call):
    user_id = call.from_user.id
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()
    insert_sql = """INSERT INTO users_wallet (user_id, first_name, last_name, wallet_creation_date, wallet_balance, username, transaction_password) VALUES (%s, %s, %s, %s, %s, %s, %s)"""

    if call.data == "cb_name_confirmation_yes":
        # bot.edit_message_reply_markup(
        #     chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

        current_datetime = datetime.datetime.now()
        sql_current_datetime_format = current_datetime.strftime(
            "%Y-%m-%d %H:%M:%S")
        wallet_balance = 0

        with bot.retrieve_data(user_id=user_id, chat_id=call.message.chat.id) as user_data:
            user_first_name, user_last_name, user_password, username = user_data[
                'first_name'],  user_data['last_name'], user_data['password'], user_data["username"]
        cursor.execute(insert_sql, (user_id, user_first_name, user_last_name,
                       sql_current_datetime_format, wallet_balance, username, user_password))
        connection.commit()
        bot.send_message(
            chat_id=call.message.chat.id, text=f"{user_first_name} {user_last_name}, your wallet has been created 👍. To add money into your wallet click /make_payment")
        bot.delete_state(user_id=user_id, chat_id=call.message.chat.id)

    elif call.data == "cb_name_confirmation_no":
        # bot.edit_message_reply_markup(
        #     chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.reply_to(
            call.message, "Ok we are going to start over 😞. Please enter your first name.")
        bot.set_state(user_id=user_id, state=MyStates.first_name,
                      chat_id=call.message.chat.id)

    cursor.close()
    connection.close()


@bot.message_handler(commands=['wallet_balance'])
def wallet_balance(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    user_id = message.from_user.id

    select_user_wallet_balance_from_user_wallet_table_sql = "SELECT wallet_balance FROM users_wallet WHERE user_id = %s;"

    cursor.execute(
        select_user_wallet_balance_from_user_wallet_table_sql, (user_id,))
    result = cursor.fetchone()

    if result:
        wallet_balance = result[0]
        bot.reply_to(
            message, f'Your wallet balance is  ₦{wallet_balance}')
    else:
        bot.reply_to(
            message, "You don't have a wallet with us 😲. To create a wallet click /create_wallet")

    cursor.close()
    connection.close()


@bot.message_handler(commands=['make_payment'])
def make_payment(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    user_id = message.from_user.id

    select_user_id_from_user_wallet_table_sql = "SELECT user_id FROM users_wallet WHERE user_id = %s;"

    cursor.execute(select_user_id_from_user_wallet_table_sql, (user_id,))
    result = cursor.fetchone()

    if result:
        markup = InlineKeyboardMarkup()
        paystack_web_app_button = InlineKeyboardButton(
            "Pay into your wallet.", web_app=WebAppInfo(url=os.getenv("PAYMENT_PAGE_URL")))
        markup.add(paystack_web_app_button)

        # the double underscore and backticks are markdown formatting.
        bot.reply_to(
            message, f"Please tap the button below\. Make sure to copy your user id it'd be needed during the process\. *Click this:* `{message.from_user.id}`", reply_markup=markup, parse_mode="MarkdownV2")
        notify_bot.send_message(
            5024452557, f"`{message.from_user.id}` might be about to make payments into their wallet or they are just testing it out\. Either way sha buckle up\. Open up gmail to receive paystack's mail\. We don't want to delay a potential long term customer\.", parse_mode="MarkdownV2")
    else:
        bot.reply_to(
            message, "You can't make payments since you don't have a wallet with us 😲. To create a wallet click /create_wallet.")

    cursor.close()
    connection.close()


@bot.message_handler(commands=['delete'])
def delete(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    u_id = message.from_user.id
    c_id = message.chat.id

    select_transaction_password_from_user_wallet_table_sql = "SELECT transaction_password, wallet_balance FROM users_wallet WHERE user_id = %s;"

    cursor.execute(
        select_transaction_password_from_user_wallet_table_sql, (u_id, ))
    result = cursor.fetchone()

    if result:
        user_password, user_wallet_balance = result
        bot.set_state(
            user_id=u_id, state=MyStates.user_wanna_delete, chat_id=c_id)
        with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
            user_data["transaction_password"] = user_password
            user_data["no_trials_left"] = 5
            user_data["wallet_balance"] = user_wallet_balance
        bot.reply_to(
            message, f"Are you sure you want to delete your wallet?", reply_markup=delete_confirmation_markup())
        bot.set_state(user_id=u_id, chat_id=c_id,
                      state=MyStates.delete_confirmation)

    else:
        bot.reply_to(
            message, "You can't delete a wallet since you don't have one yet. To create a wallet click /create_wallet.")

    cursor.close()
    connection.close()


# if we ask the user if they want to actually delete or not and rather than click a button, they enter a message again, then we prompt them with the same
# message annd buttons
@bot.message_handler(state=MyStates.delete_confirmation)
def delete_confirmation(message):
    bot.reply_to(
        message, f"Are you sure you want to delete your wallet?", reply_markup=delete_confirmation_markup())


@bot.callback_query_handler(state=MyStates.delete_confirmation, func=lambda call: call.data.startswith("cb_delete"))
def callback_query(call):
    user_id = call.from_user.id

    if call.data == "cb_delete_confirmation_yes":
        # bot.edit_message_reply_markup(
        #     chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

        bot.reply_to(
            call.message, "Please enter your password.")

        bot.set_state(user_id=user_id, state=MyStates.password_for_delete,
                      chat_id=call.message.chat.id)

    elif call.data == "cb_delete_confirmation_no":
        # bot.edit_message_reply_markup(
        #     chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.reply_to(call.message, "Great!!! You still have your wallet.")
        bot.delete_state(user_id, call.message.chat.id)


@bot.message_handler(state=MyStates.password_for_delete)
def authenticate_password_for_delete(entered_password_message):

    bot.delete_message(entered_password_message.chat.id,
                       entered_password_message.message_id)
    entered_password = entered_password_message.text
    u_id = entered_password_message.from_user.id
    c_id = entered_password_message.chat.id
    with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
        user_password = user_data["transaction_password"]
        user_wallet_balance = user_data["wallet_balance"]

    delete_user_from_transactions_table_sql = "DELETE FROM transactions WHERE sender_id = %s"
    delete_user_from_qr_info_table_sql = "DELETE FROM qr_info WHERE user_id = %s;"
    delete_user_from_user_wallet_table_sql = "DELETE FROM users_wallet WHERE user_id = %s;"

    if entered_password == user_password:
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()
        cursor.execute(delete_user_from_transactions_table_sql, (u_id,))
        cursor.execute(delete_user_from_qr_info_table_sql, (u_id,))
        cursor.execute(delete_user_from_user_wallet_table_sql, (u_id,))

        if user_wallet_balance > 100:
            # also if we delete their wallet and they still have money in it, the money is also deleted.
            # what if the person has 100.2
            # also implement the part where they give you their account number
            bot.send_message(entered_password_message.chat.id,
                             f"Your wallet has been deleted.😞😞. You should receive {user_wallet_balance - 100} in about 10 minutes.")
            # amount_to
            amount_to_send = user_wallet_balance - 100
            notify_bot.send_message(
                5024452557, f"`{entered_password_message.from_user.id}` just deleted his/her account\. You are meant to send ₦`{amount_to_send}` to them\.", parse_mode="MarkdownV2")

        else:
            bot.send_message(entered_password_message.chat.id,
                             f"Your wallet has been deleted.😞😞.")

        connection.commit()
        cursor.close()
        connection.close()
        bot.delete_state(user_id=u_id, chat_id=c_id)
        return
    else:
        user_data["no_trials_left"] -= 1
        no_trials_left = user_data["no_trials_left"]
        if no_trials_left > 0:
            bot.send_message(
                c_id, f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trials or you can click /cancel to cancel" if no_trials_left > 1 else f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trial  or you can click /cancel to cancel")
            return
        else:
            bot.send_message(
                c_id, "bruhhhhh you ran out of trials. I'm guessing you are a thief. You better give your life to Christ ✝️")
    bot.delete_state(user_id=u_id, chat_id=c_id)


@bot.message_handler(commands=['support'])
def support(message):
    bot.send_message(chat_id=message.from_user.id,
                     text="contact @adebola_duf or call +2349027929326")

# we are meant to remove a certain percentage as charges for each transaction. sha depending on your pricing.


@bot.message_handler(commands=['text_to_other'])
def initiate_send_to_other(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    sender_user_id = message.from_user.id

    select_transaction_password_from_user_wallet_table_sql = "SELECT transaction_password FROM users_wallet WHERE user_id = %s;"

    cursor.execute(select_transaction_password_from_user_wallet_table_sql,
                   (sender_user_id,))
    result = cursor.fetchone()

    if result:
        user_password = result[0]
        bot.reply_to(message, "Please enter your password.")
        bot.set_state(user_id=sender_user_id,
                      state=MyStates.password_for_text_to_other, chat_id=message.chat.id)
        with bot.retrieve_data(user_id=sender_user_id, chat_id=message.chat.id) as user_data:
            user_data['user_transaction_password'] = user_password
            user_data["no_trials_left"] = 5
    else:
        bot.reply_to(
            message, "You can't text ₦₦ to another user since you don't have a wallet with us 😲. To create a wallet click /create_wallet")

    cursor.close()
    connection.close()


@bot.message_handler(state=MyStates.password_for_text_to_other)
def authenticate_password_for_text_to_other_transactions(entered_password_message):
    u_id = entered_password_message.from_user.id
    c_id = entered_password_message.from_user.id

    bot.delete_message(
        chat_id=c_id, message_id=entered_password_message.message_id)
    entered_password = entered_password_message.text
    with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
        user_password = user_data['user_transaction_password']

    if entered_password == user_password:
        bot.send_message(c_id, "Password is correct")
        bot.send_message(
            c_id, f'Enter the user id or the username of the person you want to text ₦₦ to.')
        bot.set_state(
            user_id=u_id, state=MyStates.receiver_id_for_text_to_other, chat_id=c_id)
        return
    else:
        user_data["no_trials_left"] -= 1
        no_trials_left = user_data["no_trials_left"]
        if no_trials_left > 0:
            bot.send_message(
                c_id, f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trials or you can click /cancel to cancel" if no_trials_left > 1 else f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trial  or you can click /cancel to cancel")
            return
        else:
            bot.send_message(
                c_id, "bruhhhhh you ran out of trials. I'm guessing you are a thief. You better give your life to Christ ✝️")
    bot.delete_state(user_id=u_id, chat_id=c_id)


@bot.message_handler(state=MyStates.receiver_id_for_text_to_other)
def validate_receiver_id(receiver_user_id_or_username_message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    u_id = receiver_user_id_or_username_message.from_user.id
    c_id = receiver_user_id_or_username_message.chat.id
    is_receiver_id = True

    # This is just like if the message entered by the user is all numbers then that's a user id else its a username.
    # a problem arises when someone's username is all numbers.
    # i just checked you can't have all numbers as your username. The first character has to be a letter.
    try:
        receiver_user_id_or_username = int(
            receiver_user_id_or_username_message.text)
        if receiver_user_id_or_username == receiver_user_id_or_username_message.from_user.id:
            bot.reply_to(receiver_user_id_or_username_message,
                         "You can't text money to yourself ya big dummy 🤣. You can try again or click /cancel to cancel.")
            return
        else:
            select_receiver_id_from_user_wallet_table_sql = "SELECT user_id, username, first_name, last_name, wallet_balance FROM users_wallet WHERE user_id = %s;"

            cursor.execute(select_receiver_id_from_user_wallet_table_sql,
                           (receiver_user_id_or_username,))
            result = cursor.fetchone()

    except ValueError:
        is_receiver_id = False
        receiver_user_id_or_username = str(
            receiver_user_id_or_username_message.text)
        if receiver_user_id_or_username == receiver_user_id_or_username_message.from_user.username:
            bot.reply_to(receiver_user_id_or_username_message,
                         "You can't text money to yourself ya big dummy 🤣. You can try again or click /cancel to cancel.")
            return

        else:
            select_receiver_username_from_user_wallet_table_sql = "SELECT user_id, username, first_name, last_name, wallet_balance FROM users_wallet WHERE username = %s;"
            cursor.execute(select_receiver_username_from_user_wallet_table_sql,
                           (receiver_user_id_or_username, ))
            result = cursor.fetchone()

    if result:
        receiver_id, receiver_username, receiver_first_name, receiver_last_name, receiver_wallet_balance = result
        with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
            user_data["receiver_id"] = receiver_id
            user_data["receiver_first_name"] = receiver_first_name
            user_data["receiver_last_name"] = receiver_last_name
            user_data["receiver_wallet_balance"] = receiver_wallet_balance
            user_data["receiver_username"] = receiver_username
            user_data["is_receiver_id"] = is_receiver_id

        bot.reply_to(receiver_user_id_or_username_message,
                     f"How much do you want to text to {receiver_first_name} {receiver_last_name}?" if is_receiver_id else f"How much do you want to text to @{receiver_user_id_or_username}?")
        bot.set_state(
            user_id=u_id, state=MyStates.actual_send_to_other_state, chat_id=c_id)
    else:
        bot.reply_to(
            receiver_user_id_or_username_message, f"user id {receiver_user_id_or_username} doesn't have a wallet. Make sure you entered the correct thing. You can try again or click /cancel to cancel." if is_receiver_id else f"@{receiver_user_id_or_username} doesn't have a wallet. Make sure you entered the correct thing. You can try again or click /cancel to cancel.")

    cursor.close()
    connection.close()


@bot.message_handler(state=MyStates.actual_send_to_other_state)
def actual_send_to_other(amount_to_send_message):
    try:
        amount_to_send = Decimal(amount_to_send_message.text)
    except InvalidOperation:
        bot.send_message(amount_to_send_message.chat.id,
                         "You entered an invalid amount. 🤔. This time please enter a correct amount. #numbers only or you can click /cancel to cancel.")
        return

    sender_id = amount_to_send_message.from_user.id
    sender_user_name = amount_to_send_message.from_user.username
    c_id = amount_to_send_message.chat.id

    with bot.retrieve_data(user_id=sender_id, chat_id=c_id) as user_data:
        receiver_id = user_data["receiver_id"]
        receiver_first_name = user_data["receiver_first_name"]
        receiver_last_name = user_data["receiver_last_name"]
        receiver_wallet_balance = user_data["receiver_wallet_balance"]
        receiver_username = user_data["receiver_username"]
        is_receiver_id = user_data["is_receiver_id"]

    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    # if the person doesn't have a username, I'm going to use the first name and last name they inputted when registering.
    select_sender_firstname_lastname_from_user_wallet_table_sql = "SELECT first_name, last_name, wallet_balance FROM users_wallet WHERE user_id = %s;"
    cursor.execute(select_sender_firstname_lastname_from_user_wallet_table_sql,
                   (amount_to_send_message.from_user.id, ))
    sender_first_name, sender_last_name, sender_wallet_balance = cursor.fetchone()

    if amount_to_send > 0 and sender_wallet_balance >= amount_to_send:

        update_sender_wallet_balance_from_user_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance - %s WHERE user_id = %s;"
        cursor.execute(update_sender_wallet_balance_from_user_wallet_table_sql,
                       (amount_to_send, sender_id))

        bot.reply_to(amount_to_send_message,
                     f"You have texted ₦{amount_to_send} to {receiver_first_name} {receiver_last_name}. You have ₦{sender_wallet_balance - amount_to_send} left." if is_receiver_id else f"You have texted ₦{amount_to_send} to @{receiver_username}. You have ₦{sender_wallet_balance - amount_to_send} left.")

        current_datetime = datetime.datetime.now()

        update_receiver_wallet_balance_in_user_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance + %s WHERE user_id = %s;"
        cursor.execute(update_receiver_wallet_balance_in_user_wallet_table_sql,
                       (amount_to_send, receiver_id))

        # to check if the sender has a user_name or not
        if sender_user_name:
            bot.send_message(
                receiver_id, f"@{sender_user_name} just texted ₦{amount_to_send} to your wallet you now have ₦{receiver_wallet_balance + amount_to_send}")
        else:
            bot.send_message(receiver_id,
                             f"{sender_first_name} {sender_last_name} just texted ₦{amount_to_send} to your wallet you now have ₦{receiver_wallet_balance + amount_to_send}")

        # insert transaction details to the transaction table
        sql_current_datetime_format = current_datetime.strftime(
            "%Y-%m-%d %H:%M:%S")

        insert_sql_into_transactions_table = """INSERT INTO transactions(transaction_id, receiver_id, time_of_transaction, amount_transferred, sender_id)
        VALUES (DEFAULT, %s, %s, %s, %s)"""
        cursor.execute(insert_sql_into_transactions_table, (receiver_id,
                       sql_current_datetime_format, amount_to_send, sender_id))

    elif sender_wallet_balance < amount_to_send:
        bot.reply_to(amount_to_send_message,
                     f"You don't have up to ₦{amount_to_send} in your wallet.")

    elif amount_to_send == 0:
        bot.reply_to(amount_to_send_message,
                     "You can't text nothing 😂")
    else:
        bot.reply_to(amount_to_send_message,
                     "You can't text someone a -ve amount. Math gee 😂")

    bot.delete_state(sender_id, chat_id=c_id)

    # check chatgpt for an option where if any of the add sql or deduct sql fails, we don't do anything in the database.
    connection.commit()
    cursor.close()
    connection.close()


@bot.message_handler(commands=['transaction_history'])
def transaction_history(message):
    user_id = message.from_user.id
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()
    history = ""

    select_all_from_users_wallet_table_sql = """SELECT * FROM transactions
    WHERE sender_id = %s OR receiver_id = %s
    ORDER BY time_of_transaction DESC LIMIT 10"""

    cursor.execute(select_all_from_users_wallet_table_sql, (user_id, user_id))

    results = cursor.fetchall()

    if not results:
        bot.reply_to(
            message, "You haven't made any transactions since you created your wallet.")

    else:
        for i, row in enumerate(results):
            transaction_id, receiver_id, time_of_transaction, amount_transferred, sender_id = row
            select_first_name_last_name_from_transactions_table_sql = "SELECT first_name, last_name FROM users_wallet WHERE user_id = %s"
            if user_id == sender_id:  # in the case where i was the one who sent not received.
                cursor.execute(
                    select_first_name_last_name_from_transactions_table_sql, (receiver_id, ))
                person2_first_name, person2_last_name = cursor.fetchone()
                history += f"{i + 1}. At {time_of_transaction}, you texted ₦{amount_transferred} to {person2_first_name} {person2_last_name}\n\n"
            else:  # i.e if user_id == receiver_id in the case where i wasn't the one sending but the one receiving.
                cursor.execute(
                    select_first_name_last_name_from_transactions_table_sql, (sender_id, ))
                person2_first_name, person2_last_name = cursor.fetchone()
                history += f"{i + 1}. At {time_of_transaction}, you received ₦{amount_transferred} from {person2_first_name} {person2_last_name}\n\n"

        bot.reply_to(message, history)

    cursor.close()
    connection.close()


@bot.message_handler(commands=['create_payment_qr'])
def create_payment_qr(message):
    u_id = message.from_user.id
    c_id = message.chat.id
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()
    # let's check if the user has a wallet with us first
    select_user_id_from_users_wallet_table_sql = "SELECT user_id from users_wallet where user_id = %s"
    cursor.execute(select_user_id_from_users_wallet_table_sql, (u_id, ))
    result = cursor.fetchone()

    if result:
        bot.reply_to(message, "How much do you want to charge?")
        bot.set_state(
            user_id=u_id, state=MyStates.enter_amount_to_charge_for_create_qr_state, chat_id=c_id)
    else:
        bot.reply_to(
            message, "You don't have a wallet with us 😲. To create a wallet click /create_wallet")
    cursor.close()
    connection.close()


def generate_qr_id(cursor, charger_id):
    while True:
        # Generate a random number within your desired range
        # Adjust the range as needed
        random_number = random.randint(10000000, 99999999)

        # Check if the generated number already exists in the table
        cursor.execute(
            "SELECT COUNT(*) FROM qr_info WHERE qr_id = %s AND user_id = %s;", (random_number, charger_id))
        count = cursor.fetchone()[0]

        if count == 0:
            return random_number  # Return the unique random number


@bot.message_handler(state=MyStates.enter_amount_to_charge_for_create_qr_state)
def qr_amount_processor(amount_to_charge_message):
    try:
        amount_to_charge = Decimal(amount_to_charge_message.text)
    except InvalidOperation:
        bot.send_message(amount_to_charge_message.chat.id,
                         "You entered an invalid amount. 🤔. This time please enter a correct amount. #numbers only or you can click /cancel to cancel.")
        return

    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    charger_id = amount_to_charge_message.from_user.id
    qr_id = generate_qr_id(cursor, charger_id)

    if amount_to_charge > 0:
        insert_qr_info_into_qr_info_table_sql = "INSERT INTO qr_info (qr_id, user_id, qr_used) VALUES (%s, %s, %s)"
        cursor.execute(insert_qr_info_into_qr_info_table_sql,
                       (qr_id, charger_id, False))
        connection.commit()
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2
        )
        # qr.add_data(f"{charger_usernamme}: {amount_to_charge}{charger_id}{qr_transaction_number}")
        qr.add_data(f"{charger_id}:{amount_to_charge}:{qr_id}")
        qr_img = qr.make_image(back_color="white", fill_color='black')

        # We create a io.BytesIO buffer to store the QR code image in memory without saving it as a file.
        buffer = io.BytesIO()
        # The QR code is generated and saved to the buffer as a PNG image.
        qr_img.save(buffer, format='PNG')
        buffer.seek(0)

        # Send the QR code image as a photo message
        bot.send_photo(amount_to_charge_message.chat.id, photo=buffer)
        bot.delete_state(user_id=amount_to_charge_message.from_user.id,
                         chat_id=amount_to_charge_message.chat.id)
    elif amount_to_charge == 0:
        bot.send_message(amount_to_charge_message.chat.id,
                         "You cannot charge someone a ₦0. Trust 😂")
    else:
        bot.send_message(amount_to_charge_message.chat.id,
                         "You cannot charge someone a -ve amount. Math gee 😂")

    cursor.close()
    connection.close()


def qr_send_to_charger_confirmation_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    confirm_button = InlineKeyboardButton(
        text="Confirm ✅", callback_data="qr_send_to_charger_confirmed")
    decline_button = InlineKeyboardButton(
        text="Decline 🚫", callback_data="qr_send_to_charger_declined")
    markup.add(confirm_button, decline_button)
    return markup

# you need to handle the error where the user that created a qr has deleted their wallet. trying to retrieve the user's data would return None and indexing this would return an error
# also when a user that hasn't created a wallet is trying to create a qr or scan a qr


@bot.message_handler(commands=['scan_payment_qr'])
def scan_payment_qr(message):

    # Holy Spirit
    u_id = message.from_user.id
    c_id = message.chat.id
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()
    # let's check if the user has a wallet with us first
    select_user_id_from_users_wallet_table_sql = "SELECT user_id from users_wallet where user_id = %s"
    cursor.execute(select_user_id_from_users_wallet_table_sql, (u_id, ))
    result = cursor.fetchone()

    if result:
        markup = InlineKeyboardMarkup()
        qr_scanner_web_app = InlineKeyboardButton(
            "Scan QR", web_app=WebAppInfo(url="https://mboretto.github.io/easy-qr-scan-bot/"))
        markup.add(qr_scanner_web_app)

        bot.reply_to(message, "Make sure to copy the code generated.",
                     reply_markup=markup)
        bot.send_message(
            message.chat.id, "Enter the code generated.")
        bot.set_state(user_id=u_id, state=MyStates.qr_scanned, chat_id=c_id)
    else:
        bot.reply_to(
            message, "You don't have a wallet with us 😲. To create a wallet click /create_wallet")

    cursor.close()
    connection.close()


@bot.message_handler(state=MyStates.qr_scanned)
def qr_code_content_handler(qr_code_content_message):
    u_id = qr_code_content_message.from_user.id
    c_id = qr_code_content_message.chat.id

    qr_code_content = qr_code_content_message.text
    qr_code_content = qr_code_content.split(":")

    # this is the error handling for if a person scans a qr code not from textpay.
    try:
        charger_id, amount_to_charge, qr_id = int(qr_code_content[0]), Decimal(
            qr_code_content[1]), int(qr_code_content[2])
    except (IndexError, ValueError, InvalidOperation):
        bot.send_message(qr_code_content_message.chat.id,
                         "You scanned a wrong qr code. 😪. You can try again or click /cancel to cancel.")
        return

    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    # change the name of this user_id in the qr_info tabl to charger id
    select_qr_info_from_qr_info_table_sql = "SELECT qr_used from qr_info WHERE user_id = %s AND qr_id = %s"
    select_charger_info_from_users_wallet_table_sql = "SELECT first_name, last_name from users_wallet where user_id = %s"

    cursor.execute(
        select_charger_info_from_users_wallet_table_sql, (charger_id, ))
    result = cursor.fetchone()
    # if the charger id exists
    if result:
        name_first, name_last = result

    else:
        bot.send_message(c_id, "This QR code is invalid.")
        bot.delete_state(user_id=u_id, chat_id=c_id)
        return
    if charger_id == u_id:
        bot.send_message(
            c_id, "You can't create and scan the same qr. 😮‍💨. Now the QR is invalid")
        update_qr_used_to_true_in_qr_info_table_sql = "UPDATE qr_info SET qr_used = %s WHERE qr_id = %s"
        cursor.execute(
            update_qr_used_to_true_in_qr_info_table_sql, (True, qr_id))
        connection.commit()
        cursor.close()
        connection.close()
        bot.delete_state(user_id=u_id, chat_id=c_id)

    cursor.execute(select_qr_info_from_qr_info_table_sql, (charger_id, qr_id))
    result = cursor.fetchone()
    if result:
        retrieved_qr_used = result[0]
    else:
        bot.send_message(
            c_id, "The QR code that was scanned is not from TextPay. The person that initiated this transaction might be fraudulent. 👮🏾‍♂️")
        bot.delete_state(user_id=u_id, chat_id=c_id)

    if retrieved_qr_used == False:
        with bot.retrieve_data(u_id, c_id) as user_data:
            user_data["charger_id"] = charger_id
            user_data["amount_to_charge"] = amount_to_charge
            user_data["qr_id"] = qr_id
            user_data["no_trials_left"] = 5
            user_data["charger_first_name"] = name_first
            user_data["charger_last_name"] = name_last

        bot.send_message(qr_code_content_message.chat.id,
                         f"Are you sure you want to text ₦{amount_to_charge} to {name_first} {name_last}", reply_markup=qr_send_to_charger_confirmation_markup())
        bot.set_state(u_id, state=MyStates.qr_text_confirmation, chat_id=c_id)
    else:
        bot.send_message(qr_code_content_message.chat.id,
                         "This QR code has already been used. Ask the person to generate a new one 😊")
        bot.delete_state(user_id=u_id, chat_id=c_id)

    cursor.close()
    connection.close()

# this fucntion is for when we are asking if they want to confirm or decline the payment request but rather than click one of the 2 buttons, they type in something
# so, in the case where they type in something, we want to just show the same buttons and the message the buttons are attached to.


@bot.message_handler(state=MyStates.qr_text_confirmation)
def qr_text_confirmation(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as user_data:
        name_first = user_data["charger_first_name"]
        name_last = user_data["charger_last_name"]
        amount_to_charge = user_data["amount_to_charge"]

    bot.send_message(message.chat.id,
                     f"Are you sure you want to text ₦{amount_to_charge} to {name_first} {name_last}", reply_markup=qr_send_to_charger_confirmation_markup())


@bot.callback_query_handler(state=MyStates.qr_text_confirmation, func=lambda call: call.data.startswith("qr_send_to"))
def callback_query(call):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    select_user_password_from_users_wallet_table = "SELECT transaction_password FROM users_wallet WHERE user_id = %s"
    cursor.execute(
        select_user_password_from_users_wallet_table, (call.from_user.id, ))

    # this is going to cause an error later when a user is trying to scan a qr and they don't have a wallet because cursor.fetchone() is going to return None and we'd be trying to index none which would return a TypeError
    user_password = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as user_data:
        user_data["transaction_password"] = user_password
        charger_id = user_data["charger_id"]
    if call.data == "qr_send_to_charger_confirmed":

        # i commented this block out because now that i have implemented states, the buttons only work when the user is in this state.
        # bot.edit_message_reply_markup(
        #     chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

        bot.reply_to(
            call.message, "Enter your password to complete the transaction.")
        bot.set_state(user_id=call.from_user.id,
                      state=MyStates.password_for_qr_scan, chat_id=call.message.chat.id)

    else:
        # bot.edit_message_reply_markup(
        #     chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        # i think i want this one to send a message to both parties involved in the transaction that it has been cancelled
        bot.reply_to(call.message, "Transaction has been declined.")
        bot.send_message(
            charger_id, f"@{call.from_user.username} just declined the transaction." if call.from_user.username else f"The other person just cancelled the transaction.")
        bot.delete_state(user_id=call.from_user.id,
                         chat_id=call.message.chat.id)


# remember to include the part where the transactions table is updated


@bot.message_handler(state=MyStates.password_for_qr_scan)
def authenticate_password_for_qr_transactions(entered_password_message):
    bot.delete_message(entered_password_message.chat.id,
                       entered_password_message.message_id)
    chargee_id = entered_password_message.from_user.id
    chat_id = entered_password_message.chat.id

    with bot.retrieve_data(user_id=chargee_id, chat_id=chat_id) as user_data:
        charger_id = user_data["charger_id"]
        amount_to_charge = user_data["amount_to_charge"]
        qr_id = user_data["qr_id"]
        user_password = user_data["transaction_password"]
    entered_password = entered_password_message.text

    if entered_password == user_password:
        # the sql stuffs
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()

        select_chargers_info_from_users_wallet_table_sql = "SELECT username, first_name, last_name, wallet_balance from users_wallet WHERE user_id = %s"
        select_chargees_info_from_users_wallet_table_sql = "SELECT username, first_name, last_name, wallet_balance from users_wallet WHERE user_id = %s"

        update_chargers_wallet_balance_in_users_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance + %s where user_id = %s"
        update_chargees_wallet_balance_in_users_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance - %s where user_id = %s"

        cursor.execute(
            select_chargers_info_from_users_wallet_table_sql, (charger_id, ))
        charger_username, charger_first_name, charger_last_name, charger_wallet_balance = cursor.fetchone()
        cursor.execute(
            select_chargees_info_from_users_wallet_table_sql, (chargee_id, ))
        chargee_username, chargee_first_name, chargee_last_name, chargee_wallet_balance = cursor.fetchone()
        update_qr_used_to_true_for_the_scanned_qr_code_sql = "UPDATE qr_info SET qr_used = %s WHERE user_id = %s AND qr_id = %s"
        cursor.execute(
            update_qr_used_to_true_for_the_scanned_qr_code_sql, (True, charger_id, qr_id))

        if chargee_wallet_balance >= amount_to_charge:
            cursor.execute(
                update_chargers_wallet_balance_in_users_wallet_table_sql, (amount_to_charge, charger_id))
            cursor.execute(
                update_chargees_wallet_balance_in_users_wallet_table_sql, (amount_to_charge, chargee_id))

            current_datetime = datetime.datetime.now()
            sql_current_datetime_format = current_datetime.strftime(
                "%Y-%m-%d %H:%M:%S")

            insert_sql_into_transactions_table = """INSERT INTO transactions(transaction_id, receiver_id, time_of_transaction, amount_transferred, sender_id)
            VALUES (DEFAULT, %s, %s, %s, %s)"""
            cursor.execute(insert_sql_into_transactions_table, (charger_id,
                           sql_current_datetime_format, amount_to_charge, chargee_id))

            connection.commit()
            cursor.close()
            connection.close()
            # checking if the charger has a username else use their firstname and lastname
            if charger_username:
                bot.send_message(entered_password_message.from_user.id,
                                 f"Great!!! You have texted ₦{amount_to_charge} to @{charger_username} through qr. You have ₦{chargee_wallet_balance - amount_to_charge} left.")
                bot.send_message(
                    chat_id=charger_id, text=f"@{chargee_username} just texted ₦{amount_to_charge} to your wallet through the qr. You now have ₦{charger_wallet_balance + amount_to_charge}" if chargee_username else f"{chargee_first_name} {chargee_last_name} just texted ₦{amount_to_charge} to your wallet through the qr. You now have ₦{charger_wallet_balance + amount_to_charge}")
            else:
                bot.send_message(entered_password_message.from_user.id,
                                 f"Great!!! You have texted ₦{amount_to_charge} to {charger_first_name} {charger_last_name} through qr. You have ₦{chargee_wallet_balance - amount_to_charge} left.")
                bot.send_message(
                    chat_id=charger_id, text=f"@{chargee_username} just texted ₦{amount_to_charge} to your wallet through the qr. You now have ₦{charger_wallet_balance + amount_to_charge}" if chargee_username else f"{chargee_first_name} {chargee_last_name} just texted ₦{amount_to_charge} to your wallet through the qr. You now have ₦{charger_wallet_balance + amount_to_charge}")
        elif chargee_wallet_balance < amount_to_charge:
            bot.send_message(
                chargee_id, f"You don't have up to ₦{amount_to_charge} in your wallet.")
        else:
            bot.send_message(
                chargee_id, "You can't text someone a -ve amount. Math gee 😂")
    else:
        user_data["no_trials_left"] -= 1
        no_trials_left = user_data["no_trials_left"]
        if no_trials_left > 0:
            bot.send_message(
                chat_id, f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trials or you can click /cancel to cancel" if no_trials_left > 1 else f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trial  or you can click /cancel to cancel")
            return
        else:
            bot.send_message(
                chat_id, "bruhhhhh you ran out of trials. I'm guessing you are a thief. You better give your life to Christ ✝️")
    bot.delete_state(user_id=chargee_id, chat_id=chat_id)


@bot.message_handler(commands=["get_my_id"])
def get_my_id(message):
    bot.reply_to(
        message, f"Your ID is `{message.from_user.id}`", parse_mode="MarkdownV2")


@bot.message_handler(commands=["liquidate"])
def liquidate(message):
    u_id = message.from_user.id
    c_id = message.chat.id
    with psycopg2.connect(**connection_params) as connection:
        with connection.cursor() as cursor:
            select_user_transaction_password_from_users_wallet_sql = "SELECT transaction_password, wallet_balance FROM users_wallet WHERE user_id = %s;"
            cursor.execute(
                select_user_transaction_password_from_users_wallet_sql, (u_id, ))
            result = cursor.fetchone()
            if result:
                user_password, wallet_balance = result
                if wallet_balance < 100:
                    bot.reply_to(
                        message, f"You can't liquidate when you have less than ₦100 and you have ₦{wallet_balance} in your wallet.")
                else:
                    bot.set_state(
                        user_id=u_id, state=MyStates.liquidate_enter_password, chat_id=c_id)
                    with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
                        user_data["password"] = user_password
                        user_data["wallet_balance"] = wallet_balance
                        user_data["no_trials_left"] = 5
                    bot.reply_to(message, "Enter your transaction password. 😔")
            else:
                bot.reply_to(
                    message, "You don't have a wallet with us 😲. To create a wallet click /create_wallet")


@bot.message_handler(state=MyStates.liquidate_enter_password)
def password_authentication(message):
    u_id = message.from_user.id
    c_id = message.chat.id
    entered_password = message.text
    with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
        user_password = user_data["password"]
        wallet_balance = user_data["wallet_balance"]
        no_trials_left = user_data["no_trials_left"]
    bot.delete_message(chat_id=c_id, message_id=message.message_id)
    if entered_password != user_password:
        if no_trials_left > 0:
            bot.send_message(
                c_id, f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trials or you can click /cancel to cancel" if no_trials_left > 1 else f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trial  or you can click /cancel to cancel")
            user_data["no_trials_left"] -= 1
            return
        else:
            bot.send_message(
                c_id, "bruhhhhh you ran out of trials. I'm guessing you are a thief. You better give your life to Christ ✝️")
            bot.delete_state(user_id=u_id, chat_id=c_id)
    else:
        bot.send_message(c_id, "So, how much do you want to liquidate?")
        bot.set_state(
            u_id, state=MyStates.liquidate_enter_amount_to_liquidate, chat_id=c_id)


@bot.message_handler(state=MyStates.liquidate_enter_amount_to_liquidate)
def account_number(message):
    u_id = message.from_user.id
    c_id = message.chat.id
    try:
        amount_to_liquidate = Decimal(message.text)
    except InvalidOperation:
        bot.reply_to(
            "You entered an invalid amount. 🤔. This time please enter a correct amount. #numbers only or you can click /cancel to cancel.")
        return
    with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
        wallet_balance = user_data["wallet_balance"]
        user_data["amount_to_liquidate"] = amount_to_liquidate
    if wallet_balance < amount_to_liquidate:
        bot.send_message(
            c_id, f"You don't have up to ₦{amount_to_liquidate} in your wallet since you have only ₦{wallet_balance} left. You can try again or click /cancel to cancel.")
        return
    bot.set_state(u_id, MyStates.liquidate_enter_account_number, c_id)
    bot.reply_to(
        message, "Great!! Enter the account number to send the money to.")
    bot.set_state(message.from_user.id,
                  MyStates.liquidate_enter_account_number, message.chat.id)


@bot.message_handler(state=MyStates.liquidate_enter_account_number)
def account_number(message):
    u_id = message.from_user.id
    c_id = message.chat.id
    try:
        int(message.text)
        account_number = message.text
        if len(account_number) < 10:
            bot.send_message(
                c_id, "You entered an invalid account number. You can try again or click /cancel to cancel.")
            return
    except ValueError:
        bot.send_message(
            c_id, "You entered an invalid account number. You can try again or click /cancel to cancel.")
        return

    with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
        user_data["account_number"] = int(account_number)
    bot.reply_to(message, "Please now send the bank name.")
    bot.set_state(u_id, MyStates.liquidate_enter_bank_name, c_id)


def liquidate_confirmation_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton(text="Yes ✅", callback_data="liquidate_confirmation_yes"),
               InlineKeyboardButton(text="No 🚫", callback_data="liquidate_confirmation_no"))
    return markup


@bot.message_handler(state=MyStates.liquidate_enter_bank_name)
def liquidation_confirmation(message):
    u_id = message.from_user.id
    c_id = message.chat.id
    with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
        user_data["bank_name"] = message.text
        amount_to_liquidate = user_data["amount_to_liquidate"]
        bank_name = user_data["bank_name"]
        account_number = user_data["account_number"]
    bot.send_message(message.chat.id, f"Are you sure you want to liquidate ₦{amount_to_liquidate} to {bank_name.upper()}: {account_number}?",
                     reply_markup=liquidate_confirmation_markup())


@bot.callback_query_handler(state=MyStates.liquidate_enter_bank_name, func=lambda call: call.data.startswith("liquidate_confirmation_"))
def liquidation_confirmation(call):
    u_id = call.from_user.id
    c_id = call.message.chat.id
    if call.data == "liquidate_confirmation_yes":
        with bot.retrieve_data(user_id=u_id, chat_id=c_id) as user_data:
            user_password = user_data["password"]
            wallet_balance = user_data["wallet_balance"]
            amount_to_liquidate = user_data["amount_to_liquidate"]
            account_number = user_data["account_number"]
            bank_name = user_data["bank_name"]

        # i feel we should also represent this in the transactions table so wehen you want to see your transaaction history, you'd see a place wehn you liquidated
        update_user_wallet_balance_in_users_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance - %s WHERE user_id = %s"
        with psycopg2.connect(**connection_params) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    update_user_wallet_balance_in_users_wallet_table_sql, (amount_to_liquidate, u_id))
                connection.commit()
        notify_bot.send_message(
            5024452557, f"`{u_id}` just liquidated ₦`{amount_to_liquidate}`\. You are meant to send ₦`{amount_to_liquidate}` to acct no: `{account_number}`, bank: `{bank_name}`\.", parse_mode="MarkdownV2")
        bot.send_message(
            c_id, f"You should receive ₦{amount_to_liquidate} in about 10 minutes. And you have ₦{wallet_balance - amount_to_liquidate} left in your wallet.")
        bot.delete_state(u_id, c_id)


class UserDetails(BaseModel):
    user_id: int
    amount: Decimal


class NotificationData(BaseModel):
    chat_id: int = None
    user_id: int
    message: str
    operation: str = None
    authentication_token: str
    amount: str


@app.post("/send-notification-to-user")
def send_notification(notification_data: NotificationData):
    if notification_data.authentication_token != os.getenv("ADMIN_PASSWORD"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authentication key is wrong.")
    else:
        amount = Decimal(notification_data.amount)
        with psycopg2.connect(**connection_params) as connection:
            with connection.cursor() as cursor:
                select_user_info_from_users_wallet_table = "SELECT user_id FROM users_wallet WHERE user_id = %s;"
                cursor.execute(
                    select_user_info_from_users_wallet_table, (notification_data.user_id, ))
                result = cursor.fetchone()

                if result and notification_data.operation and notification_data.chat_id:
                    update_user_wallet_in_users_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance + %s WHERE user_id = %s;"
                    cursor.execute(
                        update_user_wallet_in_users_wallet_table_sql, (amount, notification_data.user_id))
                    connection.commit()
                    bot.send_message(text=notification_data.message,
                                     chat_id=notification_data.chat_id)
                    return JSONResponse(status_code=200,
                                        content="User notified successfully.")
                elif result and notification_data.operation and not notification_data.chat_id:
                    update_user_wallet_in_users_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance + %s WHERE user_id = %s;"
                    cursor.execute(
                        update_user_wallet_in_users_wallet_table_sql, (amount, notification_data.user_id))
                    connection.commit()
                    # beware of sending to user_id rather than chat_id incase telegramm decide to make it a must to send message using only chat id.
                    bot.send_message(text=notification_data.message,
                                     chat_id=notification_data.user_id)
                    return JSONResponse(status_code=200,
                                        content="User notified successfully.")

                elif result and notification_data.chat_id and not notification_data.operation:
                    bot.send_message(notification_data.chat_id,
                                     notification_data.message)
                    return JSONResponse(status_code=200,
                                        content="User notified successfully.")
                elif result and not notification_data.chat_id and not notification_data.operation:
                    bot.send_message(notification_data.user_id,
                                     notification_data.message)
                    return JSONResponse(status_code=200,
                                        content="User notified successfully.")
                elif not result:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                        detail=f"user id {notification_data.user_id} doesn't exist.")


bot.add_custom_filter(custom_filter=custom_filters.StateFilter(bot))
bot.add_custom_filter(custom_filter=custom_filters.IsDigitFilter())

bot.remove_webhook()

# Set webhook
bot.set_webhook(
    url=WEBHOOK_URL_BASE + textpaybot_token
)

uvicorn.run(app=app,
            host="0.0.0.0")

# this qr stuff, i think something might go wrong if a user 1 creates a qr for user 2 to scan and pay
# and before both of them are done settling the payment, user 1 creates another qr. The previous qr beomes useless and only the new qr would be the usable one/
# since the new qr woul have a new transaction number which would be the only number attached to user 1


# PROBLEMS
# When a user deletes their wallet, it deletes only transactions that they initiated. So if they click transaction history,
#  they would still see that someone texted them money. But they won't sha see that they texted anyone money

# when you want to text money to someone using their user_id, there should be a way to like confirm who you are texting to
# so a reply would be how much do you want to text to <username of the corresponding user_id> or <first name last name of the corresponding uer_id>


# so i just thought of something. how to use the bot for transactions in offline mode. so when you are online, you generate a qr code that contains your user_id,
# the amount and the id of the recipient so you can take your device around even when you are offline and you can pay for something by scanning the qr code.
# so on the pos, it scans your qr code and then asks you to input your password. if the id on the qr and the password match, then it would print the paper
# with the amount you want to pay


# if a user creates a qr before one was used, the old one would still be unused.
