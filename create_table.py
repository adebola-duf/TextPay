import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env")
db = os.get_env("DB_NAME")
db_username = os.get_env("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_EXTERNAL_HOST")
db_port = os.getenv("DB_PORT")

conn = psycopg2.connect(database=db,
                        user=db_username,
                        host=db_host,
                        password=db_password,
                        port=db_port)

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
