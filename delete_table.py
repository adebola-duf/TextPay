import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env")
db = os.getenv("DB_NAME")
db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_EXTERNAL_HOST")
db_port = os.getenv("DB_PORT")
# Replace with your connection parameters
connection = psycopg2.connect(database=db,
                              user=db_username,
                              host=db_host,
                              password=db_password,
                              port=db_port)


cursor = connection.cursor()

table_name = "users_wallet"
drop_table_query = f"DROP TABLE IF EXISTS {table_name};"
print("Table deleted successfully.")

cursor.execute(drop_table_query)

connection.commit()

cursor.close()
connection.close()
