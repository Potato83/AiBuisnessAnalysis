import os
from dotenv import load_dotenv

load_dotenv()

SQL_HOST = os.getenv("DB_HOST", "postgres")
SQL_PORT = int(os.getenv("DB_PORT", "5432"))
SQL_USER = os.getenv("POSTGRES_USER")
SQL_PASS = os.getenv("POSTGRES_PASSWORD")
SQL_DB = os.getenv("POSTGRES_DB")