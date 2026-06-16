import os
from dotenv import load_dotenv
import mysql.connector
import sqlite3

load_dotenv()

db_type = os.environ.get('DB_TYPE', 'mysql')

if db_type == 'sqlite':
    try:
        db_path = os.environ.get('DB_NAME', 'instance/pharmaplus.db')
        if db_path == 'pharmaplus':
            db_path = 'instance/pharmaplus.db'
        print(f"Connecting to SQLite database at {db_path}...")
        conn = sqlite3.connect(db_path)
        print("Connected to SQLite DB successfully!")
    except Exception as e:
        print("ERROR:", str(e))
else:
    host = os.environ.get('DB_HOST', 'localhost')
    user = os.environ.get('DB_USER', 'root')
    password = os.environ.get('DB_PASSWORD', 'Test@1234')
    db = os.environ.get('DB_NAME', 'Pharmaplus')

    try:
        print(f"Connecting to MySQL host={host}, user={user}, password={password}...")
        conn = mysql.connector.connect(host=host, user=user, password=password)
        print("Connected without DB!")
        conn.database = db
        print("Selected DB!")
    except Exception as e:
        print("ERROR:", str(e))
