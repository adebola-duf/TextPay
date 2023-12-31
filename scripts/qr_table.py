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

create_qr_table_sql = """CREATE TABLE qr_info(
qr_id SERIAL,
user_id BIGINT,
qr_used BOOLEAN,
reverse_qr BOOLEAN,
PRIMARY KEY (user_id, qr_id),
FOREIGN KEY (user_id) 
REFERENCES user_wallet(user_id)
)"""

cursor = conn.cursor()
cursor.execute(create_qr_table_sql)

# Commit the transaction
conn.commit()

print("Table 'qr_info' created successfully.")
cursor.close()
conn.close()
