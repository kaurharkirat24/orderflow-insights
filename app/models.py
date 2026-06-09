"""
ORM Models for customers, orders, and refunds.
"""

import uuid

from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False)

    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False)

    customer = relationship("Customer", back_populates="orders")
    refunds = relationship("Refund", back_populates="order")


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, nullable=False)

    order = relationship("Order", back_populates="refunds")
