import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection():
    try:
        db_conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
        if db_conn.is_connected():
            print("✅ Successful MySQL connection")
            return db_conn
    except Error as e:
        print(f"❌ MySQL connection error : {e}")
    return None
