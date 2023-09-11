import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_EXTERNAL_HOST")

conn = psycopg2.connect(database="my_pay_database",
                        user="my_pay",
                        host=db_host,
                        password=db_password,
                        port=5432)

# SQL statement to create the table
create_table_sql = """
CREATE TABLE user_wallet (
    user_id bigint PRIMARY KEY,
    wallet_balance numeric(10, 2) NOT NULL
);
"""


cursor = conn.cursor()
cursor.execute(create_table_sql)

# Commit the transaction
conn.commit()

print("Table 'user_wallet' created successfully.")
cursor.close()
conn.close()
