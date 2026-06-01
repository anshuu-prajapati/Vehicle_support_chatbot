from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def run_schema_migrations():
    from sqlalchemy import inspect

    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        columns = [column["name"] for column in inspector.get_columns("users")]
        with engine.begin() as connection:
            if "role" not in columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'customer'")
                )
            if "created_at" not in columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                )
