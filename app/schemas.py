from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Company(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str


class Bento(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    price: int


class OrderSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    order_date: str
    company_name: str
    total_price: int


class OrderItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    quantity: int
    price: int
    subtotal: int


class QuantitySelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    bento_id: int
    quantity: int

    @property
    def as_db_tuple(self) -> tuple[int, int]:
        return (self.bento_id, self.quantity)


class OrderDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_id: int
    order_date: str
    quantities: tuple[QuantitySelection, ...]
