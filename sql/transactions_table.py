import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env")
db = os.getenv("DB_NAME")
db_username = os.getenv("DB_USERNAME")
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
CREATE TABLE transactions(
transaction_id BIGSERIAL PRIMARY KEY,
receiver_id BIGINT,
time_of_transaction TIMESTAMP,
amount_transferred DECIMAL(12, 2),
paystack_transaction_reference TEXT,
sender_id BIGINT,
CONSTRAINT fk_user_wallet
FOREIGN KEY (sender_id)
REFERENCES users_wallet(user_id)
)
"""


cursor = conn.cursor()
cursor.execute(create_table_sql)

# Commit the transaction
conn.commit()

print("Table 'transactions' created successfully.")
cursor.close()
conn.close()
