import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///./cs2.db"), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
