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
    table_names = inspector.get_table_names()

    if "users" in table_names:
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

    if "conversation_states" in table_names:
        conversation_columns = [column["name"] for column in inspector.get_columns("conversation_states")]
        conversation_indexes = inspector.get_indexes("conversation_states")
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

            if "id" in conversation_columns:
                id_column = next(
                    (column for column in inspector.get_columns("conversation_states") if column["name"] == "id"),
                    None,
                )
                if id_column is not None and "INTEGER" in str(id_column["type"]).upper():
                    connection.execute(text("ALTER TABLE conversation_states DROP CONSTRAINT IF EXISTS conversation_states_pkey"))
                    connection.execute(text("ALTER TABLE conversation_states RENAME COLUMN id TO legacy_id"))
                    connection.execute(text("ALTER TABLE conversation_states ADD COLUMN id UUID NOT NULL DEFAULT gen_random_uuid()"))
                    connection.execute(text("UPDATE conversation_states SET id = gen_random_uuid() WHERE id IS NULL"))
                    connection.execute(text("ALTER TABLE conversation_states ADD PRIMARY KEY (id)"))

            if "created_at" not in conversation_columns:
                connection.execute(
                    text(
                        "ALTER TABLE conversation_states ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    )
                )

            if "updated_at" not in conversation_columns:
                connection.execute(
                    text(
                        "ALTER TABLE conversation_states ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    )
                )

            if "context_json" not in conversation_columns:
                connection.execute(
                    text(
                        "ALTER TABLE conversation_states ADD COLUMN context_json JSONB NOT NULL DEFAULT '{}'::jsonb"
                    )
                )

            has_phone_index = any(
                index["column_names"] == ["phone_number"] or "phone_number" in index["column_names"]
                for index in conversation_indexes
            )
            if not has_phone_index:
                connection.execute(
                    text("CREATE UNIQUE INDEX IF NOT EXISTS ix_conversation_states_phone_number ON conversation_states (phone_number)")
                )
