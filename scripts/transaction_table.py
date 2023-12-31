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
CREATE TABLE transaction(
transaction_id BIGSERIAL PRIMARY KEY,
receiver_id BIGINT,
time_of_transaction TIMESTAMP,
amount_transferred DECIMAL(12, 2),
paystack_transaction_reference TEXT,
type_transaction TEXT,
acct_number_liquidated_to INTEGER,
bank_acct_number_belongs_to TEXT,
sender_id BIGINT,
FOREIGN KEY (sender_id)
REFERENCES user_wallet(user_id)
)
"""

create_index_for_paystack_transaction_reference = "CREATE INDEX idx_transaction_paystack_transaction_reference ON transaction (paystack_transaction_reference);"

cursor = conn.cursor()
cursor.execute(create_table_sql)
cursor.execute(create_index_for_paystack_transaction_reference)

# Commit the transaction
conn.commit()

print("Table 'transaction' created successfully.")
cursor.close()
conn.close()
