from app.utils import get_current_time
from app.models import User_WalletUpdate, Transaction, BaseTransaction
from app.crud import update_user_wallet, create_transaction
from app.utils import verify_password
from app.crud import delete_user_wallet
from fastapi.responses import JSONResponse
from app.crud import create_user_wallet
from app.models import User_WalletCreate, User_WalletRead
from app.crud import get_user_wallet
from fastapi import FastAPI, Path, Query, HTTPException, status
import uvicorn
from typing import Optional
from pydantic import BaseModel
import psycopg2
import os
from dotenv import load_dotenv
import datetime
from decimal import Decimal
import requests

load_dotenv(".env")
db = os.getenv("DB_NAME")
db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_INTERNAL_HOST")
db_port = os.getenv("DB_PORT")
token = os.getenv("ADMIN_PASSWORD")

connection_params = {"database": db,
                     "user": db_username,
                     "host": db_host,
                     "password": db_password,
                     "port": db_port}
app = FastAPI()

# what i am doing is pretty much the database stuffs or the operations but in an API form


@app.get(path="/")
def home():
    return {"You have rechead TextPay's base endpoint."}

# the things i want to be able to do with this api is to be able to get user info, create new users, delete users, add money to users wallet balance, best user maybe by number of transactions


columns_in_users_wallet = ["user_id", "username", "first_name", "last_name",
                           "wallet_creation_date", "wallet_balance", "transaction_password"]


@app.get(path="/user-info/{authentication_token}/{user_id}", response_model=User_WalletRead)
def user_info(authentication_token: str, user_id: int):
    user = get_user_wallet(user_id=user_id)

    if authentication_token == token:
        if user:
            return user
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User doesn't exist")
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


@app.post(path="/create-wallet/{authentication_token}", response_model=User_WalletRead)
def create_user(authentication_token: str, user: User_WalletCreate):
    if authentication_token == token:
        user = get_user_wallet(user_id=User_WalletCreate.user_id)
        if not user:
            user = create_user_wallet(user)
            return user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


class DeleteAuthorization(BaseModel):
    user_id: int
    user_password: str


# delete authorization is like the stuffs needed from the user to complete the transaction.
incorrect_matric_number_or_password_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrent matric number or password.")


@app.delete(path="/delete-user-wallet/{authentication_token}", response_class=JSONResponse)
def delete_user(authentication_token, delete_authorization: DeleteAuthorization):
    if authentication_token == token:
        user = get_user_wallet(delete_authorization.user_id)
        if user:
            if verify_password(delete_authorization.user_password, user.transaction_password):
                delete_user_wallet(delete_authorization.user_id)
                return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "User Deleted"})
            raise incorrect_matric_number_or_password_exception

        else:
            raise incorrect_matric_number_or_password_exception
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


class SenderReceiver(BaseModel):
    sender_id: int
    receiver_id: int
    sender_password: str
    amount: Decimal


@app.put(path="/text-to-other/{authentication_token}")
def text_to_other(authentication_token: str, sender_receiver: SenderReceiver):
    if authentication_token == token:
        sender = get_user_wallet(user_id=SenderReceiver.sender_id)
        receiver = get_user_wallet(user_id=SenderReceiver.receiver_id)

        if sender:
            if sender.wallet_balance < sender_receiver.amount:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Sender doesn't have up to ₦{sender_receiver.amount}")
            if receiver:
                if verify_password(plain_password=sender_receiver.sender_password, hashed_password=sender.transaction_password):
                    update_user_wallet(user_id=sender.user_id, update_data=User_WalletUpdate(
                        amount_to_update_wallet_balance=sender_receiver.amount, add_amount=False))
                    update_user_wallet(user_id=receiver.user_id, update_data=User_WalletUpdate(
                        amount_to_update_wallet_balance=sender_receiver.amount, add_amount=True))
                    transaction = create_transaction(Transaction(receiver_id=receiver.id, time_of_transaction=get_current_time(
                    ), amount_transferred=sender_receiver.amount, sender_id=sender.id))

                    return BaseTransaction.model_validate(transaction).model_dump(exclude_unset=True)
                else:
                    raise incorrect_matric_number_or_password_exception
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Receiver doesn't exist.")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Sender doesn't exist.")
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


class AddToWallet(BaseModel):
    user_id: int
    amount: Decimal


@app.put(path="/add-to-wallet/{authentication_token}")
def add_to_user_wallet(authentication_token: str, add_to_wallet_details: AddToWallet):
    if authentication_token == token:
        with psycopg2.connect(**connection_params) as connection:
            with connection.cursor() as cursor:
                select_user_info_from_users_wallet_table = "SELECT * FROM users_wallet WHERE user_id = %s;"
                cursor.execute(select_user_info_from_users_wallet_table,
                               (add_to_wallet_details.user_id, ))
                user_info = cursor.fetchone()
                if user_info:
                    update_user_wallet_in_users_wallet_table_sql = "UPDATE users_wallet SET wallet_balance = wallet_balance + %s WHERE user_id = %s;"
                    cursor.execute(update_user_wallet_in_users_wallet_table_sql,
                                   (add_to_wallet_details.amount, add_to_wallet_details.user_id))
                    connection.commit()
                    data = {
                        "user_id": add_to_wallet_details.user_id,
                        "message": f"You have just added ₦{add_to_wallet_details.amount} into your wallet. Thanks for texting with us 👍😉."
                    }
                    response = requests.put(
                        f"https://textpay.onrender.com/send-notification-to-user/{token}/", json=data)

                    if response.status_code == 200:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST, detail=f"You have added ₦{add_to_wallet_details.amount} to user id: {add_to_wallet_details.user_id}'s wallet and user has been notifed about their payment of ₦{add_to_wallet_details.amount} into their wallet")
                    elif response.status_code == 401:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticatio key is wrong.")
                    elif response.status_code == 400:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                            detail=f"user id: {add_to_wallet_details.user_id} doesn't exist.")

                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail=f"user id: {add_to_wallet_details.user_id} doesn't exist")
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


@app.get("/transaction-history/{authentication_token}/{user_id}")
def transaction_history(authentication_token: str, user_id: int, number_transactions: int = Query(default=10, gt=0)):
    if authentication_token == token:
        with psycopg2.connect(**connection_params) as connection:
            with connection.cursor() as cursor:
                select_all_from_users_wallet_table_sql = """SELECT * FROM transactions
                                                            WHERE sender_id = %s OR receiver_id = %s
                                                            ORDER BY time_of_transaction DESC LIMIT %s"""

                cursor.execute(
                    select_all_from_users_wallet_table_sql, (user_id, user_id, number_transactions))
                results = cursor.fetchall()

                if not results:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail=f"User {user_id} hasn't made any transaction")
                else:
                    transaction_dict = {}
                    for i, row in enumerate(results):
                        transaction_id, receiver_id, time_of_transaction, amount_transferred, sender_id = row
                        select_first_name_last_name_from_transactions_table_sql = "SELECT first_name, last_name FROM users_wallet WHERE user_id = %s"
                        if user_id == sender_id:  # in the case where i was the one who sent not received.
                            cursor.execute(
                                select_first_name_last_name_from_transactions_table_sql, (receiver_id, ))
                            person2_first_name, person2_last_name = cursor.fetchone()
                            transaction_dict[i] = f"At {time_of_transaction}, {user_id} texted ₦{
                                amount_transferred} to {person2_first_name} {person2_last_name}"
                        else:  # i.e if user_id == receiver_id in the case where i wasn't the one sending but the one receiving.
                            cursor.execute(
                                select_first_name_last_name_from_transactions_table_sql, (sender_id, ))
                            person2_first_name, person2_last_name = cursor.fetchone()
                            transaction_dict[i] = f"At {time_of_transaction}, {user_id} received ₦{
                                amount_transferred} from {person2_first_name} {person2_last_name}"

                    return transaction_dict
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


class NotificationData(BaseModel):
    chat_id: int
    message: str


@app.post("/send-notification-to-user/{authentication_token}")
def send_notification(authentication_token, notification_data: NotificationData):
    if authentication_token != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authentication key is wrong.")
    else:
        data = {
            "chat_id": notification_data.chat_id,
            "message": notification_data.message
        }
        response = requests.post(
            f"https://textpay.onrender.com/send-notification-to-user/{token}", json=data)
        if response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Something went wrong somewhere.")
        elif response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication key is wrong.")
        else:
            raise HTTPException(status_code=status.HTTP_200_OK,
                                detail="User has been notified.")


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0")
