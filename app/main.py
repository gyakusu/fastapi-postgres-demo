from app.db import get_connection
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")


# Template helpers
def format_yen(value) -> str:
    return f"{int(value):,}円"


templates.env.filters["yen"] = format_yen


# DB queries
def fetch_companies():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name
                FROM companies
                ORDER BY name
                """
            )
            return cur.fetchall()


def fetch_bentos():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, price
                FROM bento
                ORDER BY id
                """
            )
            return cur.fetchall()


def fetch_orders():
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
                GROUP BY o.id, o.order_date, c.name
                ORDER BY o.order_date DESC, o.id DESC
                """
            )
            return cur.fetchall()


def fetch_order(order_id: int):
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
                return None, []

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

    return order, items


def insert_order(
    company_id: int,
    order_date,
    quantities: list[tuple[int, int]],
) -> int:
    with get_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orders (
                        company_id,
                        order_date,
                        created_at
                    )
                    VALUES (%s, %s, NOW())
                    RETURNING id
                    """,
                    (company_id, order_date),
                )
                order_id = cur.fetchone()[0]

                cur.executemany(
                    """
                    INSERT INTO order_items (
                        order_id,
                        bento_id,
                        quantity
                    )
                    VALUES (%s, %s, %s)
                    """,
                    [
                        (order_id, bento_id, quantity)
                        for bento_id, quantity in quantities
                    ],
                )

    return order_id


# Form parsing
def parse_company_id(value) -> int:
    if value is None:
        raise HTTPException(
            status_code=400,
            detail="company_id is required",
        )

    try:
        return int(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="company_id must be an integer",
        )


def parse_quantities(form) -> list[tuple[int, int]]:
    quantities: list[tuple[int, int]] = []

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
            status_code=400,
            detail="At least one bento quantity must be greater than zero",
        )

    return quantities


# Row conversion
def order_row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "order_date": row[1],
        "company_name": row[2],
        "total_price": row[3],
    }


def item_row_to_dict(row) -> dict:
    return {
        "name": row[0],
        "quantity": row[1],
        "price": row[2],
        "subtotal": row[3],
    }


# Routes
@app.get("/")
def index(request: Request):
    companies = fetch_companies()
    bentos = fetch_bentos()

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

    company_id = parse_company_id(form.get("company_id"))
    order_date = form.get("order_date")

    if order_date is None:
        raise HTTPException(
            status_code=400,
            detail="order_date is required",
        )

    quantities = parse_quantities(form)

    order_id = insert_order(
        company_id=company_id,
        order_date=order_date,
        quantities=quantities,
    )

    return RedirectResponse(
        url=f"/orders/complete?order_id={order_id}",
        status_code=303,
    )


@app.get("/orders")
def order_history(request: Request):
    orders = [
        order_row_to_dict(row)
        for row in fetch_orders()
    ]

    return templates.TemplateResponse(
        request,
        "order_history.html",
        {
            "orders": orders,
        },
    )


@app.get("/orders/complete")
def order_complete(request: Request, order_id: int):
    order, items = fetch_order(order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    order_data = order_row_to_dict(order)

    item_rows = [
        item_row_to_dict(item)
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
