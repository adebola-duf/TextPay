import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_EXTERNAL_HOST")

connection_params = {"database": "my_pay_database",
                     "user": "my_pay",
                     "host": db_host,
                     "password": db_password,
                     "port": "5432"}

connection = psycopg2.connect(**connection_params)
cursor = connection.cursor()

select_sql = "SELECT user_id FROM user_wallet WHERE user_id = %s;"
update_sql = "UPDATE user_wallet SET wallet_balance = wallet_balance + %s WHERE user_id = %s;"

user_id = int(
    input("Enter the user_id of the customer's wallet balance to be updated: "))
cursor.execute(select_sql, (user_id,))
result = cursor.fetchone()

if result:  # to verify if i actually inputed a correct user_id
    action = input(
        "Do you want to add or deduct from wallet balance? ").lower()
    if action == "add":
        amt_added = int(
            input(f"Enter the amount you want to add for this {user_id}: "))
        cursor.execute(update_sql, (amt_added, user_id))

        print(f"Added ₦{amt_added:.2f} from the wallet balance of {user_id}.")

    elif action == "deduct" or action == "subtract":
        amt_subtact = int(
            input(f"Enter the amount you want to deduct for this {user_id}: "))
        cursor.execute(update_sql, (-amt_subtact, user_id))

        print(
            f"Deducted ₦{amt_subtact:.2f} from the wallet balance of {user_id}.")

    connection.commit()
