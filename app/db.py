import psycopg


DATABASE_URL = "dbname=demo_db"


def get_connection():
    return psycopg.connect(DATABASE_URL)
