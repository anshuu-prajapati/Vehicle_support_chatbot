from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from urllib.parse import urlparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
        return
    
    try:
        # Parse the database URL
        parsed = urlparse(DATABASE_URL)
        db_name = parsed.path[1:]  # Remove leading slash
        
        # Create connection to postgres database (default database)
        conn_params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'user': parsed.username,
            'password': parsed.password,
            'database': 'postgres'  # Connect to default postgres database
        }
        
        # Connect to PostgreSQL server
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database '{db_name}'...")
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database '{db_name}' created successfully!")
        else:
            print(f"Database '{db_name}' already exists.")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        print("Please create the database manually or check your connection settings.")

# Create database if it doesn't exist
create_database_if_not_exists()

# Configure engine based on database type
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def run_schema_migrations():
    from sqlalchemy import inspect

    # Skip migrations for SQLite as it doesn't support all PostgreSQL features
    if DATABASE_URL.startswith("sqlite"):
        print("SQLite detected - skipping PostgreSQL-specific migrations")
        return

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
