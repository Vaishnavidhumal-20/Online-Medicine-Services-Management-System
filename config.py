import os
import mysql.connector
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """
    Direct MySQL connection using mysql-connector-python.
    """
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', 'Test@1234'),
        database=os.environ.get('DB_NAME', 'Pharmaplus')
    )

def get_database_uri():
    """
    Construct database URI from environment variables.
    Priority: DATABASE_URL (full connection string) > Individual components
    """
    # Check if full DATABASE_URL is provided
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url
    
    # Check for individual database components
    db_type = os.environ.get('DB_TYPE', 'mysql')
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '3306')  # Default MySQL port
    db_name = os.environ.get('DB_NAME', 'Pharmaplus')
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', 'Test@1234')
    
    if db_type == 'mysql' and db_host:
        # MySQL connection - URL-encode password to handle special characters
        if db_user and db_password:
            encoded_password = quote_plus(db_password)
            return f"mysql+mysqlconnector://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
        elif db_user:
            return f"mysql+mysqlconnector://{db_user}@{db_host}:{db_port}/{db_name}"
        else:
            return f"mysql+mysqlconnector://{db_host}:{db_port}/{db_name}"
    else:
        # Default to SQLite
        return 'sqlite:///pharmaplus.db'

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-pharmaplus-2024'
    # Database URI - constructed from environment variables
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Mail Config
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
