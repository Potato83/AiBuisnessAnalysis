import os
from dotenv import load_dotenv

load_dotenv()

SQL_HOST = os.getenv("SQL_HOST", "localhost")
SQL_PORT = int(os.getenv("SQL_PORT", "3306"))
SQL_USER = os.getenv("SQL_USER")
SQL_PASS = os.getenv("SQL_PASS")
SQL_DB = os.getenv("SQL_DB")