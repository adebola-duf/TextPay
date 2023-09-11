import psycopg2

conn = psycopg2.connect(database="my_pay_database",
                        user="my_pay",
                        host="dpg-cjvehft175es73fokpig-a.oregon-postgres.render.com",
                        password="ydPXwrvBadgExyMQZdu0Dv0UIesC04KF",
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
