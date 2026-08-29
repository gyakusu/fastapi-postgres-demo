from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
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


@app.post("/orders")
async def create_order(request: Request):
    form = await request.form()

    company_id_raw = form.get("company_id")
    order_date = form.get("order_date")

    if company_id_raw is None or order_date is None:
        raise HTTPException(
            status_code=400, detail="company_id and order_date are required")

    try:
        company_id = int(company_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400, detail="company_id must be an integer")

    quantities = []
    for key, value in form.items():
        if not key.startswith("quantity_"):
            continue

        try:
            bento_id = int(key.removeprefix("quantity_"))
            quantity = int(value)
        except (TypeError, ValueError):
            continue

        if quantity > 0:
            quantities.append((bento_id, quantity))

    if not quantities:
        raise HTTPException(
            status_code=400, detail="At least one bento quantity must be greater than zero")

    with get_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orders (company_id, order_date, created_at)
                    VALUES (%s, %s, NOW())
                    RETURNING id
                    """,
                    (company_id, order_date),
                )
                order_id = cur.fetchone()[0]

                for bento_id, quantity in quantities:
                    cur.execute(
                        """
                        INSERT INTO order_items (order_id, bento_id, quantity)
                        VALUES (%s, %s, %s)
                        """,
                        (order_id, bento_id, quantity),
                    )

    return RedirectResponse(url="/", status_code=303)
