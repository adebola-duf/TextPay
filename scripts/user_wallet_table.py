import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env")
db = os.getenv("DB_NAME")
db_username = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")

conn = psycopg2.connect(database=db,
                        user=db_username,
                        host=db_host,
                        password=db_password,
                        port=db_port)

# SQL statement to create the table
create_table_sql = """
CREATE TABLE user_wallet(
user_id BIGINT PRIMARY KEY,
username VARCHAR(40),
first_name VARCHAR(40),
last_name VARCHAR(40),
wallet_creation_date TIMESTAMP,
wallet_balance DECIMAL(12, 2),
transaction_password VARCHAR(40)
)
"""
create_index_for_username = "CREATE INDEX idx_user_wallet_username ON user_wallet (username);"


cursor = conn.cursor()
cursor.execute(create_table_sql)
cursor.execute(create_index_for_username)

# Commit the transaction
conn.commit()

print("Table 'user_wallet' created successfully.")
cursor.close()
conn.close()
