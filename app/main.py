from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.db import get_connection


app = FastAPI()

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def index(request: Request):
    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT id, name
                FROM companies
                ORDER BY name
                """
            )
            companies = cur.fetchall()

            cur.execute(
                """
                SELECT id, name, price
                FROM bento
                ORDER BY id
                """
            )
            bentos = cur.fetchall()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "companies": companies,
            "bentos": bentos,
        },
    )
