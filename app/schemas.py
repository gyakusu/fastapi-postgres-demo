"""Immutable application data models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Company(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str


class CompanyContact(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    order_count: int = Field(ge=0)
    last_order_date: str | None = None
    total_price: int = Field(ge=0)


class Bento(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    price: int = Field(ge=0)


class BentoAllergenInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    bento_name: str
    allergens: tuple[str, ...]


class OrderSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    order_date: str
    company_name: str
    total_price: int = Field(ge=0)


class OrderItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    quantity: int = Field(gt=0)
    price: int = Field(ge=0)
    subtotal: int = Field(ge=0)


class QuantitySelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    bento_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

    @property
    def as_db_tuple(self) -> tuple[int, int]:
        return self.bento_id, self.quantity


class OrderDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_id: int = Field(gt=0)
    order_date: str
    quantities: tuple[QuantitySelection, ...] = Field(min_length=1)
