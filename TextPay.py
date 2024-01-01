from app.utils import get_state_data
from app.models import StateDataToGet
from app.utils import update_state_data
from app.models import StateData
import os
from decimal import Decimal, InvalidOperation
from dotenv import load_dotenv

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, Message, CallbackQuery
from telebot.storage import StateMemoryStorage
from telebot import custom_filters

from fastapi import FastAPI, HTTPException, status
import uvicorn
from fastapi.responses import JSONResponse

from app.models import MyStates, User_Wallet, Transaction, QR_Info, QR_InfoUpdate, NotificationData, QRData
from app.crud import get_user_wallet, create_user_wallet, delete_user_wallet, update_user_wallet, get_transactions, update_qr_info, get_qr_info, create_qr_info
from app.utils import get_password_hash, verify_password, welcome_message, get_user_id_and_chat_id_from_message_or_call, get_current_time, create_qr

# states storage
state_storage = StateMemoryStorage()  # you can init here another storage

load_dotenv(".env")
textpaybot_token = os.getenv("TEXT_PAY_BOT_TOKEN")
notifybot_token = os.getenv("NOTIFY_BOT_TOKEN")

WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL_BASE")

bot = telebot.TeleBot(textpaybot_token, state_storage=state_storage)
notify_bot = telebot.TeleBot(notifybot_token)

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
def send_welcome(message: Message):
    reply_message = welcome_message(message)
    bot.reply_to(message=message, text=reply_message)


@bot.message_handler(state="*", commands=['cancel'])
def cancel(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    if not bot.get_state(user_id=user_id, chat_id=chat_id):
        bot.reply_to(
            message, "You are not currently performing any operations.")
        return
    bot.delete_state(user_id=user_id, chat_id=chat_id)
    bot.reply_to(message, "cancelled.")


@bot.message_handler(commands=['create_wallet'])
def create_account(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    user_wallet = get_user_wallet(user_id=user_id)

    if user_wallet:
        bot.reply_to(message, "You already have a wallet with us silly 🙃.")
    else:
        bot.reply_to(
            message, "Great, we just need some information to do that for you. If that's ok by you, click on /continue.")
    bot.set_state(user_id=user_id, state=MyStates.xontinue, chat_id=chat_id)


@bot.message_handler(state=MyStates.xontinue, commands=['continue'])
def xontinue(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    user_wallet = get_user_wallet(user_id=user_id)
    if user_wallet:
        return
    bot.send_message(user_id, "Please enter your first name.")
    bot.set_state(user_id=user_id, state=MyStates.first_name, chat_id=chat_id)

# At the beginning of evvery set of operation, we set user_data["state_datat"] toa  StateData object directly, but subsequently, we use the update_state_data function
# also for some reason, you can access the state_data outside the with block but i think i should not do that in case of future updates so my code doesn't break


@bot.message_handler(state=MyStates.first_name)
def first_name(user_first_name_message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=user_first_name_message)
    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
        user_data["state_data"] = StateData(
            first_name=user_first_name_message.text, username=user_first_name_message.from_user.username)

    bot.set_state(user_id=user_id, state=MyStates.last_name, chat_id=chat_id)
    bot.send_message(chat_id=chat_id,
                     text=f"Nice name you have 😊. {user_first_name_message.text} please enter your last name.")


@bot.message_handler(state=MyStates.last_name)
def last_name(user_last_name_message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=user_last_name_message)
    with bot.retrieve_data(user_id=user_id) as user_data:
        user_data["state_data"] = update_state_data(
            existing_state_data=user_data["state_data"], update_state_data=StateData(last_name=user_last_name_message.text))
    bot.set_state(user_id=user_id, state=MyStates.password, chat_id=chat_id)
    bot.send_message(chat_id,
                     f"One more thing. Enter a password for transactions (and remember it!) 🔒 because your text will be deleted immediately after you enter it. If forgotten, 📞 support. 😊")


@bot.message_handler(state=MyStates.password)
def password(user_password_message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=user_password_message)
    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
        user_data["set_state"] = update_state_data(existing_state_data=user_data["state_data"], update_state_data=StateData(
            transaction_password=user_password_message.text))
        state_data_gotten = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            first_name=True, last_name=True, transaction_password=True))
        user_first_name = state_data_gotten.first_name
        user_last_name = state_data_gotten.last_name
        user_transaction_password = state_data_gotten.transaction_password
    bot.delete_message(chat_id=chat_id,
                       message_id=user_password_message.message_id)
    bot.set_state(user_id=user_id, state=MyStates.registration_info_given,
                  chat_id=chat_id)
    bot.send_message(chat_id,
                     f"Just to confirm, your name is {user_first_name} {user_last_name} and your password is {'*' * len(user_transaction_password)}", reply_markup=name_confirmation_markup())


@bot.message_handler(state=MyStates.registration_info_given)
def confirmation_message(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    with bot.retrieve_data(user_id, chat_id) as user_data:
        state_data_gotten = get_state_data(
            existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(first_name=True, last_name=True, transaction_password=True))
        user_first_name, user_last_name, user_transaction_password = state_data_gotten.first_name, state_data_gotten.last_name, state_data_gotten.transaction_password
    bot.send_message(chat_id,
                     f"Just to confirm, your name is {user_first_name} {user_last_name} and your password is {'*' * len(user_transaction_password)}", reply_markup=name_confirmation_markup())


@bot.callback_query_handler(state=[MyStates.registration_info_given], func=lambda call: call.data.startswith("cb_name"))
def callback_query(call: CallbackQuery):
    print("registration info given", call.data)
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(call=call)
    if call.data == "cb_name_confirmation_yes":
        print("user pressed the yes button")
        with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
            print("entering the get state")
            state_data_gotten = get_state_data(
                existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(first_name=True, last_name=True, transaction_password=True, username=True))
            user_first_name, user_last_name, user_password, username = state_data_gotten.first_name, state_data_gotten.last_name, state_data_gotten.transaction_password, state_data_gotten.username
            print("state gotten")
        user_wallet = User_Wallet(user_id=user_id, username=username, first_name=user_first_name, last_name=user_last_name,
                                  wallet_creation_date=get_current_time(), transaction_password=get_password_hash(user_password))
        user = create_user_wallet(user_wallet=user_wallet)
        bot.send_message(
            chat_id=chat_id, text=f"{user_first_name} {user_last_name}, your wallet has been created 👍. To add money into your wallet click /make_payment")
        bot.delete_state(user_id=user_id, chat_id=chat_id)

    elif call.data == "cb_name_confirmation_no":
        bot.reply_to(
            call.message, "Ok we are going to start over 😞. Please enter your first name.")
        bot.set_state(user_id=user_id, state=MyStates.first_name,
                      chat_id=chat_id)


@bot.message_handler(commands=['wallet_balance'])
def wallet_balance(message: Message):
    user = get_user_wallet(message.from_user.id)
    if user:
        bot.reply_to(
            message, f'Your wallet balance is  ₦{user.wallet_balance}')
    else:
        bot.reply_to(
            message, "You don't have a wallet with us 😲. To create a wallet click /create_wallet")


@bot.message_handler(commands=['make_payment'])
def make_payment(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    user = get_user_wallet(user_id=user_id)

    if user:
        markup = InlineKeyboardMarkup()
        paystack_web_app_button = InlineKeyboardButton(
            "Pay into your wallet.", web_app=WebAppInfo(url=os.getenv("PAYMENT_PAGE_URL")))
        markup.add(paystack_web_app_button)
        # the double underscore and backticks are markdown formatting.
        bot.reply_to(
            message, f"Please tap the button below\. Make sure to copy your user id it'd be needed during the process\. *Click this:* `{user_id}`", reply_markup=markup, parse_mode="MarkdownV2")
    else:
        bot.reply_to(
            message, "You can't make payments since you don't have a wallet with us 😲. To create a wallet click /create_wallet.")


@bot.message_handler(commands=['delete'])
def delete(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(message)

    user = get_user_wallet(user_id=user_id)

    if user:
        bot.set_state(
            user_id=user_id, state=MyStates.user_wanna_delete, chat_id=chat_id)
        with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
            user_data["state_data"] = StateData(
                transaction_password=user.transaction_password, no_trials_left=5, wallet_balance=user.wallet_balance)
        bot.reply_to(
            message, f"Are you sure you want to delete your wallet?", reply_markup=delete_confirmation_markup())
        bot.set_state(user_id=user_id, chat_id=chat_id,
                      state=MyStates.delete_confirmation)

    else:
        bot.reply_to(
            message, "You can't delete a wallet since you don't have one yet. To create a wallet click /create_wallet.")


@bot.message_handler(state=MyStates.delete_confirmation)
def delete_confirmation(message: Message):
    bot.reply_to(
        message, f"Are you sure you want to delete your wallet?", reply_markup=delete_confirmation_markup())


@bot.callback_query_handler(state=MyStates.delete_confirmation, func=lambda call: call.data.startswith("cb_delete"))
def callback_query(call: CallbackQuery):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(call=call)

    if call.data == "cb_delete_confirmation_yes":
        bot.reply_to(
            call.message, "Please enter your password.")
        bot.set_state(user_id=user_id, state=MyStates.password_for_delete,
                      chat_id=chat_id)

    elif call.data == "cb_delete_confirmation_no":
        bot.reply_to(call.message, "Great!!! You still have your wallet.")
        bot.delete_state(user_id, chat_id)


@bot.message_handler(state=MyStates.password_for_delete)
def authenticate_password_for_delete(entered_password_message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=entered_password_message)
    bot.delete_message(chat_id,
                       entered_password_message.message_id)
    entered_password = entered_password_message.text

    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
        state_data_gotten = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            transaction_password=True, wallet_balance=True, no_trials_left=True))
        user_password = state_data_gotten.transaction_password
        user_wallet_balance = state_data_gotten.wallet_balance
        no_trials_left = state_data_gotten.no_trials_left
    if verify_password(plain_password=entered_password, hashed_password=user_password):
        delete_user_wallet(user_id=user_id)

        if user_wallet_balance > 100:
            # also if we delete their wallet and they still have money in it, the money is also deleted.
            # what if the person has 100.2
            # also implement the part where they give you their account number
            bot.send_message(chat_id,
                             f"Your wallet has been deleted.😞😞. You should receive ₦{user_wallet_balance - 100} in about 10 minutes.")
            # amount_to
            amount_to_send = user_wallet_balance - 100
            notify_bot.send_message(
                5024452557, f"`{user_id}` just deleted his/her account\. You are meant to send ₦`{amount_to_send}` to them\.", parse_mode="MarkdownV2")

        else:
            bot.send_message(chat_id,
                             f"Your wallet has been deleted.😞😞.")

    else:
        with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
            user_data["state_data"] = update_state_data(
                existing_state_data=user_data["state_data"], update_state_data=StateData(no_trials_left=no_trials_left - 1))
        if no_trials_left > 0:
            bot.send_message(
                chat_id, f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trials or you can click /cancel to cancel" if no_trials_left > 1 else f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trial  or you can click /cancel to cancel")
            return
        else:
            bot.send_message(
                chat_id, "bruhhhhh you ran out of trials. I'm guessing you are a thief. You better give your life to Christ ✝️")
    bot.delete_state(user_id=user_id, chat_id=chat_id)


@bot.message_handler(commands=['support'])
def support(message):
    bot.send_message(chat_id=message.chat.id,
                     text="contact \@adebola\_duf or call `\+2349027929326`\.", parse_mode="MarkdownV2")

# we are meant to remove a certain percentage as charges for each transaction. sha depending on your pricing.


@bot.message_handler(commands=['text_to_other'])
def initiate_send_to_other(message: Message):
    sender_user_id, sender_chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    sender = get_user_wallet(user_id=sender_user_id)

    if sender:
        sender_password = sender.transaction_password
        bot.reply_to(message, "Please enter your password.")
        bot.set_state(user_id=sender_user_id,
                      state=MyStates.password_for_text_to_other, chat_id=sender_chat_id)
        with bot.retrieve_data(user_id=sender_user_id, chat_id=sender_chat_id) as user_data:
            user_data["state_data"] = StateData(
                transaction_password=sender_password, no_trials_left=5)

    else:
        bot.reply_to(
            message, "You can't text ₦₦ to another user since you don't have a wallet with us 😲. To create a wallet click /create_wallet")


@bot.message_handler(state=MyStates.password_for_text_to_other)
def authenticate_password_for_text_to_other_transactions(entered_password_message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=entered_password_message)

    bot.delete_message(
        chat_id=chat_id, message_id=entered_password_message.message_id)
    entered_password = entered_password_message.text
    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
        state_data_gotten = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            transaction_password=True, no_trials_left=True))
        user_password = state_data_gotten.transaction_password
        no_trials_left = state_data_gotten.no_trials_left

    if verify_password(entered_password, user_password):
        bot.send_message(chat_id, "Password is correct")
        bot.send_message(
            chat_id, f'Enter the user id or the username of the person you want to text ₦₦ to.')
        bot.set_state(
            user_id=user_id, state=MyStates.receiver_id_for_text_to_other, chat_id=chat_id)
        return
    else:
        # for some reason you can still access user_data even when you are outside the with block
        user_data["state_data"] = update_state_data(
            existing_state_data=user_data["state_data"], update_state_data=StateData(no_trials_left=no_trials_left - 1))
        if no_trials_left > 0:
            bot.send_message(
                chat_id, f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trials or you can click /cancel to cancel" if no_trials_left > 1 else f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trial  or you can click /cancel to cancel")
            return
        else:
            bot.send_message(
                chat_id, "bruhhhhh you ran out of trials. I'm guessing you are a thief. You better give your life to Christ ✝️")
    bot.delete_state(user_id=user_id, chat_id=chat_id)


@bot.message_handler(state=MyStates.receiver_id_for_text_to_other)
def validate_receiver_id(receiver_id_or_username_message: Message):
    sender_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=receiver_id_or_username_message)
    is_receiver_id = True

    try:
        receiver_id = int(
            receiver_id_or_username_message.text)
        if receiver_id == sender_id:
            bot.reply_to(receiver_id_or_username_message,
                         "You can't text money to yourself ya big dummy 🤣. You can try again or click /cancel to cancel.")
            return
        else:
            receiver = get_user_wallet(
                user_id=receiver_id)

    except ValueError:
        is_receiver_id = False
        receiver_username = receiver_id_or_username_message.text
        if receiver_username == receiver_id_or_username_message.from_user.username:
            bot.reply_to(receiver_id_or_username_message,
                         "You can't text money to yourself ya big dummy 🤣. You can try again or click /cancel to cancel.")
            return

        else:
            receiver = get_user_wallet(username=receiver_username)

    if receiver:
        with bot.retrieve_data(user_id=sender_id, chat_id=chat_id) as user_data:
            # This update keyword in the model_validate only works because we used SQLModel for StateData instead of BaseModel. And it pretty much justs adds that is_receiver_id to the model
            # user_data["state_data"] = set_state_data(
            #     existing_state_data=user_data["state_data"], update_state_data=StateData.model_validate(obj=receiver.model_dump(exclude_unset=True), update={"is_receiver_id": is_receiver_id}))
            user_data["state_data"] = StateData(receiver_id=receiver.user_id, receiver_first_name=receiver.first_name, receiver_last_name=receiver.last_name,
                                                receiver_wallet_balance=receiver.wallet_balance, receiver_username=receiver.username, is_receiver_id=is_receiver_id)
        bot.reply_to(receiver_id_or_username_message,
                     f"How much do you want to text to {receiver.first_name} {receiver.last_name}?" if is_receiver_id else f"How much do you want to text to @{receiver_username}?")
        bot.set_state(
            user_id=sender_id, state=MyStates.actual_send_to_other_state, chat_id=chat_id)
    else:
        bot.reply_to(
            receiver_id_or_username_message, f"user id {receiver_id} doesn't have a wallet. Make sure you entered the correct thing. You can try again or click /cancel to cancel." if is_receiver_id else f"@{receiver_username} doesn't have a wallet. Make sure you entered the correct thing. You can try again or click /cancel to cancel.")


@bot.message_handler(state=MyStates.actual_send_to_other_state)
def actual_send_to_other(amount_to_send_message: Message):
    sender_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=amount_to_send_message)
    try:
        amount_to_send = Decimal(amount_to_send_message.text)
    except InvalidOperation:
        bot.send_message(chat_id,
                         "You entered an invalid amount. 🤔. This time please enter a correct amount. #numbers only or you can click /cancel to cancel.")
        return

    sender_user_name = amount_to_send_message.from_user.username
    with bot.retrieve_data(user_id=sender_id, chat_id=chat_id) as user_data:
        state_data_gotten = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            receiver_id=True, receiver_first_name=True, receiver_last_name=True, receiver_username=True, is_receiver_id=True))
        receiver_id = state_data_gotten.receiver_id
        receiver_first_name = state_data_gotten.receiver_first_name
        receiver_last_name = state_data_gotten.receiver_last_name
        receiver_username = state_data_gotten.receiver_username
        is_receiver_id = state_data_gotten.is_receiver_id

    sender = get_user_wallet(sender_id)
    sender_first_name, sender_last_name, sender_wallet_balance = sender.first_name, sender.last_name, sender.wallet_balance

    if amount_to_send > 0 and sender.wallet_balance >= amount_to_send:
        transaction = Transaction(receiver_id=receiver_id, time_of_transaction=get_current_time(),
                                  amount_transferred=amount_to_send, sender_id=sender_id, type_transaction="transfer")
        sender, receiver = update_user_wallet(
            user_id=sender_id, transaction=transaction)
        bot.reply_to(amount_to_send_message,
                     f"You have texted ₦{amount_to_send} to {receiver_first_name} {receiver_last_name}. You have ₦{sender.wallet_balance} left." if is_receiver_id else f"You have texted ₦{amount_to_send} to @{receiver_username}. You have ₦{sender.wallet_balance} left.")

        if sender_user_name:
            bot.send_message(
                receiver_id, f"@{sender_user_name} just texted ₦{amount_to_send} to your wallet you now have ₦{receiver.wallet_balance}")
        else:
            bot.send_message(receiver_id,
                             f"{sender_first_name} {sender_last_name} just texted ₦{amount_to_send} to your wallet you now have ₦{receiver.wallet_balance}")

    elif sender_wallet_balance < amount_to_send:
        bot.reply_to(amount_to_send_message,
                     f"You don't have up to ₦{amount_to_send} in your wallet. You have only ₦{sender.wallet_balance} left. You can try again or click /cancel to cancel")
        return

    elif amount_to_send == 0:
        bot.reply_to(amount_to_send_message,
                     "You can't text nothing 😂.This time please enter a correct amount. #numbers only or you can click /cancel to cancel.")
        return
    else:
        bot.reply_to(amount_to_send_message,
                     "You can't text someone a -ve amount. Math gee 😂. This time please enter a correct amount. #numbers only or you can click /cancel to cancel.")
        return

    bot.delete_state(sender_id, chat_id=chat_id)


@bot.message_handler(commands=['transaction_history'])
def transaction_history(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    history = ""

    user = get_user_wallet(user_id=user_id)
    if not user:
        bot.reply_to(
            message, "You don't have a wallet with us 😲. To create a wallet click /create_wallet")

    transactions_when_user_is_sender = get_transactions(sender_id=user_id)
    transactions_when_user_is_receiver = get_transactions(receiver_id=user_id)
    if not transactions_when_user_is_receiver:
        all_transactions = transactions_when_user_is_sender
    elif not transactions_when_user_is_sender:
        all_transactions = transactions_when_user_is_receiver
    elif transactions_when_user_is_receiver and transactions_when_user_is_sender:
        all_transactions = transactions_when_user_is_sender + \
            transactions_when_user_is_receiver
    if all_transactions == []:
        bot.reply_to(
            message, "You haven't made any transactions since you created your wallet.")

    else:
        for i, transaction in enumerate(all_transactions):

            if transaction.type_transaction == "paystack_payment":
                history += f"{i + 1}. At {transaction.time_of_transaction}, you paid ₦{transaction.amount_transferred} into your wallet.\n\n"
            # in the case where i was the one who sent not received.
            elif transaction.type_transaction == "transfer":
                if user_id == transaction.sender_id:
                    receiver = get_user_wallet(user_id=transaction.receiver_id)
                    history += f"{i + 1}. At {transaction.time_of_transaction}, you texted ₦{transaction.amount_transferred} to {receiver.first_name} {receiver.last_name}.\n\n"
                # i.e if user_id == receiver_id in the case where i wasn't the one sending but the one receiving.
                elif user_id == transaction.receiver_id:
                    sender = get_user_wallet(user_id=transaction.sender_id)
                    history += f"{i + 1}. At {transaction.time_of_transaction}, you received ₦{transaction.amount_transferred} from {sender.first_name} {sender.last_name}.\n\n"

            elif transaction.type_transaction == "liquidate":
                history += f"{i + 1}. At {transaction.time_of_transaction}, you liquidated ₦{transaction.amount_transferred} to Acct Number: {transaction.acct_number_liquidated_to} Bank: {transaction.bank_acct_number_belongs_to}.\n\n"
        bot.reply_to(message, history)


@bot.message_handler(commands=['create_payment_qr'])
def create_payment_qr(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    charger = get_user_wallet(user_id=user_id)

    if charger:
        bot.reply_to(message, "How much do you want to charge?")
        bot.set_state(
            user_id=user_id, state=MyStates.enter_amount_to_charge_for_create_qr_state, chat_id=chat_id)
    else:
        bot.reply_to(
            message, "You don't have a wallet with us 😲. To create a wallet click /create_wallet")


@bot.message_handler(state=MyStates.enter_amount_to_charge_for_create_qr_state)
def qr_amount_processor(amount_to_charge_message: Message):
    charger_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=amount_to_charge_message)
    try:
        amount_to_charge = Decimal(amount_to_charge_message.text)
    except InvalidOperation:
        bot.send_message(chat_id,
                         "You entered an invalid amount. 🤔. This time please enter a correct amount. #numbers only or you can click /cancel to cancel.")
        return
    if get_qr_info(user_id=charger_id) != []:
        qr: QR_Info = get_qr_info(user_id=charger_id)[-1]
        qr_id = qr.qr_id + 1
    else:
        qr_id = 1

    if amount_to_charge > 0:
        buffer = create_qr(QRData(user_id=charger_id,
                           amount_to_charge=amount_to_charge, qr_id=qr_id))
        create_qr_info(QR_Info(user_id=charger_id, qr_id=qr_id))
        bot.send_photo(chat_id, photo=buffer)
        bot.delete_state(user_id=charger_id, chat_id=chat_id)
    elif amount_to_charge == 0:
        bot.send_message(chat_id, "You cannot charge someone a ₦0. Trust 😂")
    else:
        bot.send_message(
            chat_id, "You cannot charge someone a -ve amount. Math gee 😂")


def qr_send_to_charger_confirmation_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    confirm_button = InlineKeyboardButton(
        text="Confirm ✅", callback_data="qr_send_to_charger_confirmed")
    decline_button = InlineKeyboardButton(
        text="Decline 🚫", callback_data="qr_send_to_charger_declined")
    markup.add(confirm_button, decline_button)
    return markup


@bot.message_handler(commands=['scan_payment_qr'])
def scan_payment_qr(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    # Holy Spirit
    user = get_user_wallet(user_id=user_id)

    if user:
        markup = InlineKeyboardMarkup()
        qr_scanner_web_app = InlineKeyboardButton(
            "Scan QR", web_app=WebAppInfo(url=os.getenv("QR_SCAN_URL")))
        markup.add(qr_scanner_web_app)

        bot.reply_to(message, "Make sure to copy the code generated.",
                     reply_markup=markup)
        bot.send_message(
            chat_id, "Enter the code generated.")
        bot.set_state(user_id=user_id,
                      state=MyStates.qr_scanned, chat_id=chat_id)
    else:
        bot.reply_to(
            message, "You don't have a wallet with us 😲. To create a wallet click /create_wallet")


@bot.message_handler(state=MyStates.qr_scanned)
def scanned_qr_code_content_handler(qr_code_content_message: Message):
    chargee_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=qr_code_content_message)
    qr_code_content = qr_code_content_message.text
    qr_code_content = qr_code_content.split(":")

    # this is the error handling for if a person scans a qr code not from textpay.
    try:
        charger_id, amount_charger_wants_to_charge, qr_id = int(qr_code_content[0]), Decimal(
            qr_code_content[1]), int(qr_code_content[2])
    except (IndexError, ValueError, InvalidOperation):
        bot.send_message(qr_code_content_message.chat.id,
                         "You scanned a wrong qr code. 😪. You can try again or click /cancel to cancel.")
        return

    charger = get_user_wallet(user_id=charger_id)

    # if the charger exists
    if charger:
        charger_first_name, charger_last_name = charger.first_name, charger.last_name

    else:
        bot.send_message(
            chat_id, "The QR code that was scanned is not from TextPay. The person that initiated this transaction might be fraudulent. 👮🏾‍♂️")
        bot.delete_state(user_id=chargee_id, chat_id=chat_id)
        return
    if charger_id == chargee_id:
        bot.send_message(
            chat_id, "You can't create and scan the same qr. 😮‍💨. Now the QR is invalid")
        update_qr_info(QR_InfoUpdate(
            qr_id=qr_id, user_id=charger_id, qr_used=True))
        bot.delete_state(user_id=chargee_id, chat_id=chat_id)
        return

    qr_info = get_qr_info(qr_id=qr_id, user_id=charger_id)
    print("qr info", qr_info)

    if qr_info:
        if qr_info.qr_used == False:
            with bot.retrieve_data(chargee_id, chat_id) as user_data:
                user_data["state_data"] = StateData(charger_id=charger_id, amount_to_charge=amount_charger_wants_to_charge,
                                                    qr_id=qr_id, no_trials_left=5, charger_first_name=charger_first_name, charger_last_name=charger_last_name)
            bot.set_state(
                chargee_id, state=MyStates.qr_text_confirmation, chat_id=chat_id)
            bot.send_message(chat_id,
                             f"Are you sure you want to text ₦{amount_charger_wants_to_charge} to {charger_first_name} {charger_last_name}", reply_markup=qr_send_to_charger_confirmation_markup())
        else:
            bot.send_message(qr_code_content_message.chat.id,
                             "This QR code has already been used. Ask the person to generate a new one 😊")
            bot.delete_state(user_id=chargee_id, chat_id=chat_id)

    else:
        bot.send_message(
            chat_id, "The QR code that was scanned is not from TextPay. The person that initiated this transaction might be fraudulent. 👮🏾‍♂️")
        bot.delete_state(user_id=chargee_id, chat_id=chat_id)


# this fucntion is for when we are asking if they want to confirm or decline the payment request but rather than click one of the 2 buttons, they type in something
# so, in the case where they type in something, we want to just show the same buttons and the message the buttons are attached to.
@bot.message_handler(state=MyStates.qr_text_confirmation)
def qr_text_confirmation(message: Message):
    chargee_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    with bot.retrieve_data(user_id=chargee_id, chat_id=chat_id) as user_data:
        state_data_gotten = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            charger_first_name=True, charger_last_name=True, amount_to_charge=True))
        charger_first_name = state_data_gotten.charger_first_name
        charger_last_name = state_data_gotten.charger_last_name
        amount_charger_wants_to_charge = state_data_gotten.amount_to_charge

    bot.send_message(chat_id,
                     f"Are you sure you want to text ₦{amount_charger_wants_to_charge} to {charger_first_name} {charger_last_name}", reply_markup=qr_send_to_charger_confirmation_markup())


@bot.callback_query_handler(state=MyStates.qr_text_confirmation, func=lambda call: call.data.startswith("qr_send_to"))
def callback_query(call: CallbackQuery):
    chargee_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        call=call)
    chargee = get_user_wallet(user_id=chargee_id)

    with bot.retrieve_data(chargee_id, chat_id) as user_data:
        user_data["state_data"] = update_state_data(existing_state_data=user_data["state_data"], update_state_data=StateData(
            transaction_password=chargee.transaction_password))
        state_data_gotten = get_state_data(
            existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(charger_id=True, qr_id=True))
        charger_id = state_data_gotten.charger_id
        qr_id = state_data_gotten.qr_id
    if call.data == "qr_send_to_charger_confirmed":
        bot.reply_to(
            call.message, "Enter your password to complete the transaction.")
        bot.set_state(user_id=chargee_id,
                      state=MyStates.password_for_qr_scan, chat_id=chat_id)

    else:
        bot.reply_to(call.message, "Transaction has been declined.")
        update_qr_info(QR_InfoUpdate(
            qr_id=qr_id, user_id=charger_id, qr_used=True))
        bot.send_message(
            charger_id, f"@{call.from_user.username} just declined the transaction. The QR is now invalid." if call.from_user.username else f"The other person just cancelled the transaction. The QR is now invalid.")
        bot.delete_state(user_id=chargee_id,
                         chat_id=chat_id)


@bot.message_handler(state=MyStates.password_for_qr_scan)
def authenticate_password_for_qr_transactions(entered_password_message: Message):
    chargee_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=entered_password_message)
    bot.delete_message(chat_id,
                       entered_password_message.message_id)

    with bot.retrieve_data(user_id=chargee_id, chat_id=chat_id) as user_data:
        state_data_gotten = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            charger_id=True, amount_to_charge=True, qr_id=True, transaction_password=True, no_trials_left=True))
        charger_id = state_data_gotten.charger_id
        amount_to_charge = state_data_gotten.amount_to_charge
        qr_id = state_data_gotten.qr_id
        chargee_password = state_data_gotten.transaction_password
        no_trials_left = state_data_gotten.no_trials_left
    entered_password = entered_password_message.text

    if verify_password(entered_password, chargee_password):
        update_qr_info(QR_InfoUpdate(
            qr_id=qr_id, user_id=charger_id, qr_used=True))

        transaction = Transaction(receiver_id=charger_id, time_of_transaction=get_current_time(),
                                  amount_transferred=amount_to_charge, sender_id=chargee_id, type_transaction="transfer")

        chargee, charger = update_user_wallet(transaction=transaction)
        if chargee.wallet_balance >= amount_to_charge:
            # subtract from chargee and add to charger

            # checking if the charger has a username else use their firstname and lastname
            if charger.username:
                bot.send_message(chargee_id,
                                 f"Great!!! You have texted ₦{amount_to_charge} to @{charger.username} through qr. You have ₦{chargee.wallet_balance} left.")
                bot.send_message(
                    chat_id=charger_id, text=f"@{chargee.username} just texted ₦{amount_to_charge} to your wallet through the qr. You now have ₦{charger.wallet_balance}")
            else:
                bot.send_message(chargee_id,
                                 f"Great!!! You have texted ₦{amount_to_charge} to {charger.first_name} {charger.last_name} through qr. You have ₦{chargee.wallet_balance} left.")
                bot.send_message(
                    chat_id=charger_id, text=f"@{chargee.username} just texted ₦{amount_to_charge} to your wallet through the qr. You now have ₦{charger.wallet_balance}" if chargee.username else f"{chargee.first_name} {chargee.last_name} just texted ₦{amount_to_charge} to your wallet through the qr. You now have ₦{charger.wallet_balance}")
        else:
            bot.send_message(
                chargee_id, f"You don't have up to ₦{amount_to_charge} in your wallet.")

    else:
        with bot.retrieve_data(user_id=chargee_id, chat_id=chat_id) as user_data:
            user_data["state_data"] = update_state_data(
                existing_state_data=user_data["state_data"], update_state_data=StateData(no_trials_left=no_trials_left - 1))
        if no_trials_left > 0:
            bot.send_message(
                chat_id, f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trials or you can click /cancel to cancel" if no_trials_left > 1 else f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trial  or you can click /cancel to cancel")
            return
        else:
            bot.send_message(
                chat_id, "bruhhhhh you ran out of trials. I'm guessing you are a thief. You better give your life to Christ ✝️")
    bot.delete_state(user_id=chargee_id, chat_id=chat_id)


@bot.message_handler(commands=["get_my_id"])
def get_my_id(message: Message):
    bot.reply_to(
        message, f"Your ID is `{message.from_user.id}`", parse_mode="MarkdownV2")


@bot.message_handler(commands=["liquidate"])
def liquidate(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    user = get_user_wallet(user_id=user_id)

    if user:
        user_password, wallet_balance = user.transaction_password, user.wallet_balance
        if wallet_balance < 100:
            bot.reply_to(
                message, f"You can't liquidate when you have less than ₦100 and you have ₦{wallet_balance} in your wallet.")
        else:
            bot.set_state(
                user_id=user_id, state=MyStates.liquidate_enter_password, chat_id=chat_id)
            with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
                user_data["state_data"] = StateData(
                    transaction_password=user_password, wallet_balance=wallet_balance, no_trials_left=5)

            bot.reply_to(message, "Enter your transaction password. 😔")
    else:
        bot.reply_to(
            message, "You don't have a wallet with us 😲. To create a wallet click /create_wallet")


@bot.message_handler(state=MyStates.liquidate_enter_password)
def password_authentication(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    entered_password = message.text
    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
        state_data_gotten = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            transaction_password=True, no_trials_left=True))
        user_password = state_data_gotten.transaction_password
        no_trials_left = state_data_gotten.no_trials_left
    bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    if not verify_password(entered_password, user_password):
        user_data["state_data"] = update_state_data(
            existing_state_data=user_data["state_data"], update_state_data=StateData(no_trials_left=no_trials_left - 1))
        if no_trials_left > 0:
            bot.send_message(
                chat_id, f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trials or you can click /cancel to cancel" if no_trials_left > 1 else f"You are sooo wrong. See your head like ole. 🤣😂. You have {no_trials_left} more trial  or you can click /cancel to cancel")
            return
        else:
            bot.send_message(
                chat_id, "bruhhhhh you ran out of trials. I'm guessing you are a thief. You better give your life to Christ ✝️")
            bot.delete_state(user_id=user_id, chat_id=chat_id)
    else:
        bot.send_message(chat_id, "So, how much do you want to liquidate?")
        bot.set_state(
            user_id, state=MyStates.liquidate_enter_amount_to_liquidate, chat_id=chat_id)


@bot.message_handler(state=MyStates.liquidate_enter_amount_to_liquidate)
def account_number(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    try:
        amount_to_liquidate = Decimal(message.text)
    except InvalidOperation:
        bot.reply_to(
            "You entered an invalid amount. 🤔. This time please enter a correct amount. #numbers only or you can click /cancel to cancel.")
        return
    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
        wallet_balance = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            wallet_balance=True)).wallet_balance
        user_data["state_data"] = update_state_data(
            existing_state_data=user_data["state_data"], update_state_data=StateData(amount_to_liquidate=amount_to_liquidate))
    if amount_to_liquidate < 100:
        bot.send_message(
            chat_id=chat_id, text="You can't liquidate less than ₦100. Try again or click /cancel to cancel")
        return
    if wallet_balance < amount_to_liquidate:
        bot.send_message(
            chat_id, f"You don't have up to ₦{amount_to_liquidate} in your wallet since you have only ₦{wallet_balance} left. You can try again or click /cancel to cancel.")
        return
    bot.set_state(user_id, MyStates.liquidate_enter_account_number, chat_id)
    bot.reply_to(
        message, "Great!! Enter the account number to send the money to.")
    bot.set_state(message.from_user.id,
                  MyStates.liquidate_enter_account_number, message.chat.id)


def bank_name_reply_markup():
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.row_width = 2
    with open('banks.txt', 'r') as file:
        for banks in file.readlines():
            markup.add(KeyboardButton(banks.strip()))
    return markup


@bot.message_handler(state=MyStates.liquidate_enter_account_number)
def account_number(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    try:
        account_number = message.text
        if len(account_number) < 10:
            bot.send_message(
                chat_id, "You entered an invalid account number. You can try again or click /cancel to cancel.")
            return
    except ValueError:
        bot.send_message(
            chat_id, "You entered an invalid account number. You can try again or click /cancel to cancel.")
        return

    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
        user_data["state_data"] = update_state_data(
            existing_state_data=user_data["state_data"], update_state_data=StateData(account_number=account_number))
    bot.reply_to(message, "Please now send the bank name. Enter one of the options presented in the keyboard.",
                 reply_markup=bank_name_reply_markup())
    bot.set_state(user_id, MyStates.liquidate_enter_bank_name, chat_id)


def liquidate_confirmation_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton(text="Yes ✅", callback_data="liquidate_confirmation_yes"),
               InlineKeyboardButton(text="No 🚫", callback_data="liquidate_confirmation_no"))
    return markup


@bot.message_handler(state=MyStates.liquidate_enter_bank_name)
def liquidation_confirmation(message: Message):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        message=message)
    bank_name = message.text
    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
        with open('banks.txt', 'r') as file:
            if message.text not in [banks.strip() for banks in file.readlines()]:
                bot.send_message(
                    "you entered an invalid bank name. You can try again or click /cancel.", reply_markup=bank_name_reply_markup())
                return
        user_data["state_data"] = update_state_data(
            existing_state_data=user_data["state_data"], update_state_data=StateData(bank_name=bank_name))
        state_data_gotten = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            amount_to_liquidate=True, bank_name=True, account_number=True))
        amount_to_liquidate = state_data_gotten.amount_to_liquidate
        bank_name = state_data_gotten.bank_name
        account_number = state_data_gotten.account_number
    bot.send_message(message.chat.id, f"Are you sure you want to liquidate ₦{amount_to_liquidate} to {bank_name}: {account_number}?",
                     reply_markup=liquidate_confirmation_markup())


@bot.callback_query_handler(state=MyStates.liquidate_enter_bank_name, func=lambda call: call.data.startswith("liquidate_confirmation"))
def liquidation_confirmation(call: CallbackQuery):
    user_id, chat_id = get_user_id_and_chat_id_from_message_or_call(
        call=call)

    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as user_data:
        state_data_gotten = get_state_data(existing_state_data=user_data["state_data"], state_data_to_get=StateDataToGet(
            wallet_balance=True, amount_to_liquidate=True, account_number=True, bank_name=True))
        wallet_balance = state_data_gotten.wallet_balance
        amount_to_liquidate = state_data_gotten.amount_to_liquidate
        account_number = state_data_gotten.account_number
        bank_name = state_data_gotten.bank_name
    if call.data == "liquidate_confirmation_no":
        bot.send_message(
            chat_id=chat_id, text=f"Great!! You still have ₦{wallet_balance} in your wallet.", reply_markup=ReplyKeyboardRemove())
        bot.delete_state(user_id, chat_id)

    elif call.data == "liquidate_confirmation_yes":

        sender = update_user_wallet(transaction=Transaction(time_of_transaction=get_current_time(
        ), amount_transferred=amount_to_liquidate, sender_id=user_id, acct_number_liquidated_to=account_number, bank_acct_number_belongs_to=bank_name, type_transaction="liquidate"))
        notify_bot.send_message(
            5024452557, f"`{user_id}` just liquidated ₦`{amount_to_liquidate}`\. You are meant to send ₦`{amount_to_liquidate}` to acct no: `{account_number}`, bank: `{bank_name}`\.", parse_mode="MarkdownV2")
        bot.send_message(
            chat_id, f"You should receive ₦{amount_to_liquidate} to {bank_name}: {account_number} in about 10 minutes. And you have ₦{sender.wallet_balance} left in your wallet.", reply_markup=ReplyKeyboardRemove())
        bot.delete_state(user_id, chat_id)


@app.post("/send-notification-to-user")
def send_notification(notification_data: NotificationData):
    if notification_data.authentication_token != os.getenv("ADMIN_PASSWORD"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authentication key is wrong.")
    else:
        user_id = notification_data.user_id
        chat_id = notification_data.chat_id

        user_wallet = get_user_wallet(user_id=user_id)

        if user_wallet and notification_data.operation:
            user = update_user_wallet(transaction=Transaction(time_of_transaction=notification_data.time_of_payment,
                                                              sender_id=user_id, paystack_transaction_reference=notification_data.paystack_payment_reference, amount_transferred=notification_data.amount, type_transaction="paystack_payment"))
            if chat_id:
                bot.send_message(text=notification_data.message,
                                 chat_id=chat_id)
            else:
                # beware of sending to user_id rather than chat_id incase telegramm decide to make it a must to send message using only chat id.
                bot.send_message(text=notification_data.message,
                                 chat_id=user_id)

            return JSONResponse(status_code=200,
                                content="User notified successfully.")

        elif user_wallet and not notification_data.operation:
            if chat_id:
                bot.send_message(chat_id,
                                 notification_data.message)
            else:
                bot.send_message(user_id,
                                 notification_data.message)
            return JSONResponse(status_code=200,
                                content="User notified successfully.")

        elif not user_wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"user id {notification_data.user_id} doesn't exist.")


bot.add_custom_filter(custom_filter=custom_filters.StateFilter(bot))
bot.add_custom_filter(custom_filter=custom_filters.IsDigitFilter())

bot.remove_webhook()

# Set webhook
bot.set_webhook(
    url=WEBHOOK_URL_BASE + textpaybot_token
)
if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0")

bot.polling()

# PROBLEMS

# so i just thought of something. how to use the bot for transactions in offline mode. so when you are online, you generate a qr code that contains your user_id,
# the amount and the id of the recipient so you can take your device around even when you are offline and you can pay for something by scanning the qr code.
# so on the pos, it scans your qr code and then asks you to input your password. if the id on the qr and the password match, then it would print the paper
# with the amount you want to pay
