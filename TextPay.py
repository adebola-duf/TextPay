import os
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from pathlib import Path
import pandas as pd
import psycopg2
import datetime
from decimal import Decimal
import qrcode
import io
import random
import qrcode
import time


load_dotenv(".env")
token = os.getenv("TEXT_PAY_BOT_TOKEN")
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


def delete_confirmation_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Yes", callback_data="cb_delete_confirmation_yes"),
               InlineKeyboardButton("No", callback_data="cb_delete_confirmation_no"))
    return markup


# def name_confirmation_markup():
#     markup = InlineKeyboardMarkup()
#     markup.row_width = 2
#     markup.add(InlineKeyboardButton("Yes", callback_data="cb_name_confirmation_yes"),
#                InlineKeyboardButton("No", callback_data="cb_name_confirmation_no"))
#     return markup


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.from_user.username:
        bot.reply_to(message, f"""Hi, how are you doing {message.from_user.username}?
Welcome to TextPay. What would you like to do today?
This is a list of the commands:
/create_wallet - To create a wallet.
                
/wallet_balance - To know how much you have in your wallet.
                
/make_payment - To add money into your wallet.
                
/text_to_other - To text money to another user.
                     
/create_payment_qr - Generate a QR code for accepting payments.
                     
/scan_payment_qr - To scan a QR code for making payment.
                
/transaction_history - To see your last 10 transaction history.
                
/purchase_history - To check your purchase history.
                
/delete - To Delete your wallet. We are supposed to refund the money but I haven't implemented that yet.
                
/support - For support information.""")
    else:
        bot.reply_to(message, f"""Hi, how are you doing?
Welcome to TextPay. What would you like to do today?
This is a list of the commands:
/create_wallet - To create a wallet.
                
/wallet_balance - To know how much you have in your wallet.
                
/make_payment - To add money into your wallet.
                
/text_to_other - To text money to another user.
                     
/create_payment_qr - Generate a QR code for accepting payments.
                     
/scan_payment_qr - To scan a QR code for making payment.
                     
/transaction_history - To see your last 10 transaction history.
                
/purchase_history - To check your purchase history.
                
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
    user_first_name_message = bot.send_message(
        message.from_user.id, "Please enter your first name.")
    bot.register_next_step_handler(
        user_first_name_message, first_name, user_id)

    cursor.close()
    connection.close()


def first_name(user_first_name_message, user_id):
    user_first_name = user_first_name_message.text
    user_last_name_message = bot.send_message(
        user_id, f"Nice name you have 😊. {user_first_name} please enter your last name.")
    bot.register_next_step_handler(
        user_last_name_message, last_name, user_first_name, user_id)


def last_name(user_last_name_message, user_first_name, user_id):
    user_last_name = user_last_name_message.text
    user_password_message = bot.send_message(
        user_id, "One more thing. Enter a password for transactions (and remember it!) 🔒 because your text will be deleted immediately after you enter it. If forgotten, 📞 support. 😊")
    bot.register_next_step_handler(user_password_message, password, user_last_name,
                                   user_first_name, user_id)


def password(user_password_message, user_last_name, user_first_name, user_id):
    bot.delete_message(user_password_message.chat.id,
                       user_password_message.message_id)
    user_password = user_password_message.text
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    insert_sql = """INSERT INTO users_wallet (user_id, first_name, last_name, wallet_creation_date, wallet_balance, username, transaction_password)
    VALUES (%s, %s, %s, %s, %s, %s, %s)"""

    current_datetime = datetime.datetime.now()
    sql_current_datetime_format = current_datetime.strftime(
        "%Y-%m-%d %H:%M:%S")
    wallet_balance = 0
    user_name = user_password_message.from_user.username
    cursor.execute(insert_sql, (user_id, user_first_name,
                   user_last_name, sql_current_datetime_format, wallet_balance, user_name, user_password))
    connection.commit()
    cursor.close()
    connection.close()
    bot.send_message(user_id,
                     f"{user_first_name} {user_last_name}, your wallet has been created 👍.")
# def last_name(user_last_name_message, user_first_name):
#     user_last_name = user_last_name_message.text
#     bot.send_message(user_last_name_message.from_user.id, f"Just to confirm, you name is {user_first_name} {user_last_name}", reply_markup=name_confirmation_markup)

# @bot.callback_query_handler(func=lambda call: call.data.startswith("cb_name"))
# def callback_query(call):
#     connection = psycopg2.connect(**connection_params)
#     cursor = connection.cursor()

#     if call.data == "cb_name_confirmation_yes":
#         bot.edit_message_reply_markup(
#             chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
#         bot.reply_to(call.message, "Your wallet has been created.")

#     elif call.data == "cb_name_confirmation_no":
#         bot.edit_message_reply_markup(
#             chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
#         bot.reply_to(call.message, "Great!!! You still have your wallet.")

#     cursor.close()
#     connection.close()


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
            message, "You don't have a wallet with us. To create a wallet click /create_wallet")

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
            "Pay into your wallet.", web_app=WebAppInfo(url="https://paystack.com/pay/TextPay"))
        markup.add(paystack_web_app_button)

        # the double underscore and backticks are markdown formatting.
        bot.reply_to(
            message, f"Please tap the button below\. Make sure to copy your user id it'd be needed during the process\. *Click this:* `{message.from_user.id}`", reply_markup=markup, parse_mode="MarkdownV2")
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

    select_user_id_from_user_wallet_table_sql = "SELECT user_id FROM users_wallet WHERE user_id = %s;"

    cursor.execute(select_user_id_from_user_wallet_table_sql, (user_id,))
    result = cursor.fetchone()

    if result:
        bot.reply_to(
            message, f"Are you sure you want to delete your wallet?", reply_markup=delete_confirmation_markup())
    else:
        bot.reply_to(
            message, "You can't delete a wallet since you don't have one yet. To create a wallet click /create_wallet.")

    cursor.close()
    connection.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("cb_delete"))
def callback_query(call):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    user_id = call.from_user.id

    
    select_transaction_password_from_user_wallet_table_sql = "SELECT transaction_password FROM users_wallet WHERE user_id = %s"

    if call.data == "cb_delete_confirmation_yes":
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        cursor.execute(select_transaction_password_from_user_wallet_table_sql, (user_id,))
        user_password = cursor.fetchone()[0]

        entered_password_message = bot.reply_to(call.message, "Please enter your password.")
       
        bot.register_next_step_handler(entered_password_message, authenticate_password_for_delete, user_password, call)

        cursor.close()
        connection.close()

   

    elif call.data == "cb_delete_confirmation_no":
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.reply_to(call.message, "Great!!! You still have your wallet.")

    cursor.close()
    connection.close()

def authenticate_password_for_delete(entered_password_message, user_password, call): 
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    bot.delete_message(entered_password_message.chat.id, entered_password_message.message_id)
    entered_password = entered_password_message.text
    user_id = entered_password_message.from_user.id

    delete_user_from_transactions_table_sql = "DELETE FROM transactions WHERE sender_id = %s"
    delete_user_from_user_wallet_table_sql = "DELETE FROM users_wallet WHERE user_id = %s;"

    if entered_password == user_password:
        cursor.execute(delete_user_from_transactions_table_sql, (user_id,))
        cursor.execute(delete_user_from_user_wallet_table_sql, (user_id,))
        bot.reply_to(call.message, "Your wallet has been deleted.😞😞")
        connection.commit()
    else:
        bot.send_message(entered_password_message.from_user.id, "You are sooo wrong. See your head like ole. Now you have to start over. 🤣😂")


@bot.message_handler(commands=['support'])
def support(message):
    bot.send_message(chat_id=message.from_user.id,
                     text="contact @adebola_duf or call +2349027929326")


@bot.message_handler(commands=['text_to_other'])
def initiate_send_to_other(message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    sender_user_id = message.from_user.id

    select_transaction_password_from_user_wallet_table_sql = "SELECT transaction_password FROM users_wallet WHERE user_id = %s;"

    cursor.execute(select_transaction_password_from_user_wallet_table_sql,
                   (sender_user_id,))
    user_password = cursor.fetchone()[0]

    if user_password:
        entered_password_message = bot.reply_to(message, "Please enter your password.")
       
        bot.register_next_step_handler(entered_password_message, authenticate_password_for_text_to_other_transactions, user_password)
    else:
        bot.reply_to(
            message, "You can't text ₦₦ to another user since you don't have a wallet with us. To create a wallet click /create_wallet")

    cursor.close()
    connection.close()

def authenticate_password_for_text_to_other_transactions(entered_password_message, user_password): 
    bot.delete_message(entered_password_message.chat.id, entered_password_message.message_id)
    entered_password = entered_password_message.text
    if entered_password == user_password:
        bot.send_message(entered_password_message.from_user.id, "Password is correct")
        receiver_user_id_or_username_message = bot.send_message(entered_password_message.from_user.id, f'Enter the user id or the username of the person you want to text ₦₦ to.')
        bot.register_next_step_handler(
                    receiver_user_id_or_username_message, validate_receiver_id)
    else:
        bot.send_message(entered_password_message.from_user.id, "You are sooo wrong. See your head like ole. Now you have to start over. 🤣😂")

def validate_receiver_id(receiver_user_id_or_username_message):
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()
    is_receiver_id = True

    # This is just like if the message entered by the user is all numbers then that's a user id else its a username.
    # a problem arises when someone's username is all numbers.
    # i just checked you can't have all numbers as your username. The first character has to be a letter.
    try:
        receiver_user_id_or_username = int(
            receiver_user_id_or_username_message.text)
        if receiver_user_id_or_username == receiver_user_id_or_username_message.from_user.id:
            bot.reply_to(receiver_user_id_or_username_message,
                         "You can't text money to yourself ya big dummy 🤣")
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
                         "You can't text money to yourself ya big dummy 🤣")
            return
        else:
            select_receiver_username_from_user_wallet_table_sql = "SELECT user_id, username, first_name, last_name, wallet_balance FROM users_wallet WHERE username = %s;"
            cursor.execute(select_receiver_username_from_user_wallet_table_sql,
                           (receiver_user_id_or_username, ))
            result = cursor.fetchone()

    if result:
        receiver_id, receiver_username, receiver_first_name, receiver_last_name, receiver_wallet_balance = result
        amount_to_send_message = bot.reply_to(
            receiver_user_id_or_username_message, f"How much do you want to text to {receiver_user_id_or_username}?" if is_receiver_id else f"How much do you want to text to @{receiver_user_id_or_username}?")
        bot.register_next_step_handler(
            amount_to_send_message, actual_send_to_other, receiver_user_id_or_username, is_receiver_id, receiver_id, receiver_username, receiver_first_name, receiver_last_name, receiver_wallet_balance)
    else:
        bot.reply_to(
            receiver_user_id_or_username_message, f"user_id {receiver_user_id_or_username} doesn't have a wallet. Make sure you entered the correct thing." if is_receiver_id else f"@{receiver_user_id_or_username} doesn't have a wallet. Make sure you entered the correct thing.")

    cursor.close()
    connection.close()


def actual_send_to_other(amount_to_send_message, receiver_user_id_or_username, is_receiver_id, receiver_id, receiver_username, receiver_first_name, receiver_last_name, receiver_wallet_balance):
    amount_to_send = Decimal(amount_to_send_message.text)
    sender_id = amount_to_send_message.from_user.id

    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    sender_user_name = amount_to_send_message.from_user.username
    # if the person doesn't have a username, I'm going to use the first name and last name they inputted when registering.
    select_sender_firstname_lastname_from_user_wallet_table_sql = "SELECT first_name, last_name, wallet_balance FROM users_wallet WHERE user_id = %s;"
    cursor.execute(select_sender_firstname_lastname_from_user_wallet_table_sql,
                   (amount_to_send_message.from_user.id, ))
    result = cursor.fetchone()
    sender_first_name, sender_last_name, sender_wallet_balance = result

    if amount_to_send > 0 and sender_wallet_balance >= amount_to_send:

        update_sender_wallet_balance_from_user_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance - %s WHERE user_id = %s;"
        cursor.execute(update_sender_wallet_balance_from_user_wallet_table_sql,
                       (amount_to_send, sender_id))
        bot.reply_to(amount_to_send_message,
                     f"You have texted ₦{amount_to_send} to {receiver_user_id_or_username}. You have ₦{sender_wallet_balance - amount_to_send} left." if is_receiver_id else f"You have texted ₦{amount_to_send} to @{receiver_user_id_or_username}. You have ₦{sender_wallet_balance - amount_to_send} left.")
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
    else:
        bot.reply_to(amount_to_send_message,
                     "You can't text someone a -ve number. Math gee 😂")

    # check chatgpt for an option where if any of the add sql or deduct sql fails, we don't do anything in the database.
    connection.commit()
    cursor.close()
    connection.close()

# for now, the transaction history only shows you the history of you sending and not you receiving
# later i'm goin to make it also show where you received.


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
    amount_to_charge_message = bot.reply_to(message, "How much do you want to charge?")
    bot.register_next_step_handler(amount_to_charge_message, qr_amount_processor)
    
def qr_amount_processor(amount_to_charge_message):

    amount_to_charge = Decimal(amount_to_charge_message.text)
    charger_id = amount_to_charge_message.from_user.id
    charger_usernamme = amount_to_charge_message.from_user.username
    qr_transaction_number = random.randint(1000000000, 3000000000)

    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    update_qr_transactions_password_in_users_wallet_sql = """ UPDATE users_wallet SET qr_transaction_number = %s WHERE user_id = %s RETURNING user_id;"""

    cursor.execute(update_qr_transactions_password_in_users_wallet_sql, (qr_transaction_number, charger_id))
    charger_id_from_users_wallet_table = cursor.fetchone()

    if charger_id_from_users_wallet_table:
        connection.commit()
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2
        )
        # qr.add_data(f"{charger_usernamme}: {amount_to_charge}{charger_id}{qr_transaction_number}")
        qr.add_data(f"{charger_id}:{amount_to_charge}:{qr_transaction_number}")
        qr_img = qr.make_image(back_color="white", fill_color='black')

        # We create a io.BytesIO buffer to store the QR code image in memory without saving it as a file.
        buffer = io.BytesIO()
        # The QR code is generated and saved to the buffer as a PNG image.
        qr_img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Send the QR code image as a photo message
        bot.send_photo(amount_to_charge_message.chat.id, photo=buffer)
    else:
        # User does not exist
        bot.send_message(amount_to_charge_message.chat.id, "Dude or Lady create a wallet first.")


    cursor.close()
    connection.close()

def qr_send_to_charger_confirmation_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    confirm_button = InlineKeyboardButton(text="Confirm ✅", callback_data="qr_send_to_charger_confirmed")
    decline_button = InlineKeyboardButton(text="Decline 🚫", callback_data="qr_send_to_charger_declined")
    markup.add(confirm_button, decline_button)
    return markup
    
@bot.message_handler(commands=['scan_payment_qr'])
def scan_payment_qr(message):

    markup = InlineKeyboardMarkup()
    qr_scanner_web_app = InlineKeyboardButton(
        "Scan QR", web_app=WebAppInfo(url="https://qr-code-scanner-two.vercel.app/"))
    markup.add(qr_scanner_web_app)

    bot.reply_to(message, "Make sure to copy the code generated.", reply_markup=markup)
    time.sleep(2.5)
    qr_code_content_message = bot.send_message(message.chat.id, "Enter the code generated.")
    bot.register_next_step_handler(qr_code_content_message, qr_code_content_handler)

qr_charger_id_dict = {}
qr_amount_to_charge_dict = {}

def qr_code_content_handler(qr_code_content_message):

    qr_code_content = qr_code_content_message.text
    qr_code_content = qr_code_content.split(":")

    charger_id = int(qr_code_content[0])
    qr_charger_id_dict[qr_code_content_message.from_user.id] = charger_id

    amount_to_charge = Decimal(qr_code_content[1])
    qr_amount_to_charge_dict[qr_code_content_message.from_user.id] = amount_to_charge

    qr_transaction_number = int(qr_code_content[2])

    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    select_charger_id_from_users_wallet_table = "SELECT qr_transaction_number, first_name, last_name from users_wallet where user_id = %s"
    cursor.execute(select_charger_id_from_users_wallet_table, (charger_id, ))
    result = cursor.fetchone()
    retrieved_transaction_number, name_first, name_last = result
    if retrieved_transaction_number == qr_transaction_number:
        bot.send_message(qr_code_content_message.chat.id, f"Are you sure you want to send ₦{amount_to_charge} to {name_first} {name_last}", reply_markup=qr_send_to_charger_confirmation_markup())
    else:
        bot.send_message(qr_code_content_message.chat.id, "The QR code that was scanned is not from TextPay, that person that initiated this transaction might be fraudulent.")
    cursor.close()
    connection.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("qr_send_to"))
def callback_query(call):
    
    if call.data == "qr_send_to_charger_confirmed":
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()

        select_user_password_from_users_wallet_table = "SELECT transaction_password FROM users_wallet WHERE user_id = %s"
        cursor.execute(select_user_password_from_users_wallet_table, (call.from_user.id, ))
        user_password = cursor.fetchone()[0]
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

        entered_pasword_message = bot.reply_to(call.message, "Enter your password to complete the transaction.")
        bot.register_next_step_handler(entered_pasword_message, authenticate_password_for_qr_transactions, user_password)

    elif call.data == "qr_send_to_charger_declined":
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        # i think i want this one to send a message to both parties involved in the transaction that it has been cancelled
        bot.reply_to(call.message, "Transaction has been cancelled.")
    cursor.close()
    connection.close()

# remember to include the part where the transactions table is updated
def authenticate_password_for_qr_transactions(entered_password_message, user_password): 
    bot.delete_message(entered_password_message.chat.id, entered_password_message.message_id)
    chargee_id = entered_password_message.from_user.id
    charger_id = qr_charger_id_dict[chargee_id]
    amount_to_charge = qr_amount_to_charge_dict[chargee_id]

    entered_password = entered_password_message.text

    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    select_chargers_info_from_users_wallet_table_sql = "SELECT username, first_name, last_name, wallet_balance from users_wallet WHERE user_id = %s"
    select_chargees_info_from_users_wallet_table_sql = "SELECT username, first_name, last_name, wallet_balance from users_wallet WHERE user_id = %s"

    update_chargers_wallet_balance_in_users_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance + %s where user_id = %s"
    update_chargees_wallet_balance_in_users_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance - %s where user_id = %s"

    cursor.execute(select_chargers_info_from_users_wallet_table_sql, (charger_id, ))
    charger_username, charger_first_name, charger_last_name, charger_wallet_balance = cursor.fetchone()
    cursor.execute(select_chargees_info_from_users_wallet_table_sql, (chargee_id, ))
    chargee_username, chargee_first_name, chargee_last_name, chargee_wallet_balance = cursor.fetchone()

    if entered_password == user_password:
        if chargee_wallet_balance >= amount_to_charge:
            cursor.execute(update_chargers_wallet_balance_in_users_wallet_table_sql, (amount_to_charge, charger_id))
            cursor.execute(update_chargees_wallet_balance_in_users_wallet_table_sql, (amount_to_charge, chargee_id))

            current_datetime = datetime.datetime.now()
            sql_current_datetime_format = current_datetime.strftime("%Y-%m-%d %H:%M:%S")

            insert_sql_into_transactions_table = """INSERT INTO transactions(transaction_id, receiver_id, time_of_transaction, amount_transferred, sender_id)
            VALUES (DEFAULT, %s, %s, %s, %s)"""
            cursor.execute(insert_sql_into_transactions_table, (charger_id, sql_current_datetime_format, amount_to_charge, chargee_id))
            # checking if the charger has a username else use their firstname and lastname
            if charger_username:
                bot.send_message(entered_password_message.from_user.id, f"Great!!! You have texted ₦{amount_to_charge} to @{charger_username}. You have ₦{chargee_wallet_balance - amount_to_charge} left.")
                bot.send_message(chat_id=charger_id, text=f"@{chargee_username} just texted ₦{amount_to_charge} to your wallet you now have ₦{charger_wallet_balance + amount_to_charge}" if chargee_username else f"{chargee_first_name} {chargee_last_name} just texted ₦{amount_to_charge} to your wallet you now have ₦{charger_wallet_balance + amount_to_charge}")
            else:
                bot.send_message(entered_password_message.from_user.id, f"Great!!! You have texted ₦{amount_to_charge} to {charger_first_name} {charger_last_name} . You have ₦{chargee_wallet_balance - amount_to_charge} left.")
                bot.send_message(chat_id=charger_id, text=f"@{chargee_username} just texted ₦{amount_to_charge} to your wallet you now have ₦{charger_wallet_balance + amount_to_charge}" if chargee_username else f"{chargee_first_name} {chargee_last_name} just texted ₦{amount_to_charge} to your wallet you now have ₦{charger_wallet_balance + amount_to_charge}")
        elif chargee_wallet_balance < amount_to_charge:
            bot.send_message(chargee_id, f"You don't have up to ₦{amount_to_charge} in your wallet.")
        else:
            bot.send_message(chargee_id, "You can't text someone a -ve number. Math gee 😂")
    else:
        bot.send_message(entered_password_message.from_user.id, "You are sooo wrong. See your head like ole. Now you have to start over. 🤣😂")
        bot.send_message()

    connection.commit()
    cursor.close()
    connection.close()


bot.polling()



#this qr stuff, i think something might go wrong if a user 1 creates a qr for user 2 to scan and pay
# and before both of them are done settling the payment, user 1 creates another qr. The previous qr beomes useless and only the new qr would be the usable one/
# since the new qr woul have a new transaction number which would be the only number attached to user 1



# implement the get my id
# where i stopped today is the place where whether to use username of user_id got confusing. I already started converting the querying with user id in my code
# but then again, i just thought that not every telegram user has a username. so it might not work well. but then everyone has a user id. So i'm thinking,
# since i mandate people to give me their names at the start, maybe i'm going to use their names when they text money to others. So like the message you'd be
# seeing would be something like <first name> <last name> texted you x amount.

# PROBLEMS
# When a user deletes their wallet, it deletes only transactions that they initiated. So if they click transaction history,
#  they would still see that someone texted them money. But they won't sha see that they texted anyone money

# when you want to text money to someone using their user_id, there should be a way to like confirm who you are texting to
# so a reply would be how much do you want to text to <username of the corresponding user_id> or <first name last name of the corresponding uer_id>


# so i just thought of something. how to use the bot for transactions in offline mode. so when you are online, you generate a qr code that contains your user_id,
# the amount and the id of the recipient so you can take your device around even when you are offline and you can pay for something by scanning the qr code.
# so on the pos, it scans your qr code and then asks you to input your password. if the id on the qr and the password match, then it would print the paper
# with the amount you want to pay.