from fastapi import FastAPI
import psycopg


DATABASE_URL = "dbname=demo_db"


app = FastAPI()


def get_connection():
    return psycopg.connect(DATABASE_URL)


def create_table():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE
                )
                """
            )


@app.on_event("startup")
def startup():
    create_table()


@app.get("/")
def root():
    return {"message": "Hello FastAPI + PostgreSQL!"}


@app.post("/users")
def create_user(name: str, email: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (name, email)
                VALUES (%s, %s)
                RETURNING id, name, email
                """,
                (name, email),
            )

            user = cur.fetchone()

    return {
        "id": user[0],
        "name": user[1],
        "email": user[2],
    }


@app.get("/users")
def get_users():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, email
                FROM users
                ORDER BY id
                """
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "email": row[2],
        }
        for row in rows
    ]
