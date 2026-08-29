from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import get_connection


app = FastAPI()

templates = Jinja2Templates(directory="app/templates")


def format_yen(value):
    return f"{int(value):,}円"


templates.env.filters["yen"] = format_yen


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

    return RedirectResponse(
        url=f"/orders/complete?order_id={order_id}", status_code=303
    )


@app.get("/orders/complete")
def order_complete(request: Request, order_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    o.id,
                    o.order_date,
                    c.name AS company_name,
                    COALESCE(SUM(b.price * oi.quantity), 0) AS total_price
                FROM orders o
                JOIN companies c
                    ON c.id = o.company_id
                LEFT JOIN order_items oi
                    ON oi.order_id = o.id
                LEFT JOIN bento b
                    ON b.id = oi.bento_id
                WHERE o.id = %s
                GROUP BY o.id, o.order_date, c.name
                """,
                (order_id,),
            )
            order = cur.fetchone()

            if order is None:
                raise HTTPException(status_code=404, detail="Order not found")

            cur.execute(
                """
                SELECT
                    b.name,
                    oi.quantity,
                    b.price,
                    b.price * oi.quantity AS subtotal
                FROM order_items oi
                JOIN bento b
                    ON b.id = oi.bento_id
                WHERE oi.order_id = %s
                ORDER BY b.id
                """,
                (order_id,),
            )
            items = cur.fetchall()

    order_data = {
        "id": order[0],
        "order_date": order[1],
        "company_name": order[2],
        "total_price": order[3],
    }

    item_rows = [
        {
            "name": item[0],
            "quantity": item[1],
            "price": item[2],
            "subtotal": item[3],
        }
        for item in items
    ]

    return templates.TemplateResponse(
        request,
        "order_complete.html",
        {
            "order": order_data,
            "items": item_rows,
        },
    )
