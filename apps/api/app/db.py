import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


url = os.environ.get("DATABASE_URL", "sqlite:///./cs2.db")
engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3} if url.startswith("postgresql") else {})
SessionLocal = sessionmaker(bind=engine)
