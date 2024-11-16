import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.sql import func

engine = create_engine(
    f"postgresql://{os.environ['MONGO_USER']}:{os.environ['MONGO_PASSWORD']}@{os.environ['MONGO_HOST']}/{os.environ['MONGO_DB']}"
)
session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()



class BaseModel(Base):
    """
    Base class to handle database model defaults
    this avoids repetition of common fields
    """

    __abstract__ = True

    id = Column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Primary key for the resource",
    )
    created_at = Column(
        DateTime,
        server_default=func.now(),
        comment="Records the time the record was created",
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Records the time the record was last updated",
    )


class User(BaseModel):
    __tablename__ = "users"

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
        comment="Email address of the user, used for login",
    )
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    first_name = Column(String)
    last_name = Column(String)
    phone_number = Column(Integer)
    address = Column(String)


class Pricing(BaseModel):
    __tablename__ = "pricing"

    name = Column(String)
    description = Column(String)
    default_price = Column(Float)
    currency = Column(String)
    product_type = Column(String)
    discount = Column(Float)


class Orders(BaseModel):
    __tablename__ = "orders"

    status = Column(String)
    posted_at = Column(Float)
    transacted_at = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    users = relationship("Users", back_populates="orders", lazy="joined")


class Billing(BaseModel):
    __tablename__ = "billing"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float)
    currency = Column(String)
    payment_method = Column(String)
    address = Column(String)
    city = Column(String)
    country = Column(String)
    postal_code = Column(Integer)
    vat_number = Column(String)

    users = relationship("Users", back_populates="billing", lazy="joined")
    orders = relationship("Orders", back_populates="billing", lazy="joined")


class CheckoutDetails(BaseModel):
    __tablename__ = "checkout_details"

    price = Column(Integer)
    transacted_at = Column(Float)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    pricing_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    billing_id = Column(Integer, ForeignKey("billing.id"), nullable=False)
    orders = relationship("Orders", back_populates="order_details", lazy="joined")
