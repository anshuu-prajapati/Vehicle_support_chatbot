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
        indexes = inspector.get_indexes("users")
        with engine.begin() as connection:
            if "role" not in columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'driver'")
                )
            else:
                connection.execute(
                    text("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'driver'")
                )
                connection.execute(
                    text("UPDATE users SET role = 'driver' WHERE role = 'customer'")
                )

            if "created_at" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    )
                )

            has_phone_index = any(
                index["column_names"] == ["phone"] or "phone" in index["column_names"]
                for index in indexes
            )
            if not has_phone_index:
                connection.execute(
                    text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_number ON users (phone)")
                )

            has_role_index = any(
                index["column_names"] == ["role"] or "role" in index["column_names"]
                for index in indexes
            )
            if not has_role_index:
                connection.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)")
                )
