-- Migration: Add created_at, default role, and production-ready indexes for users

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    phone VARCHAR(20) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'driver',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE users ALTER COLUMN role SET DEFAULT 'driver';
UPDATE users SET role = 'driver' WHERE role = 'customer';

ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_users_phone_number ON users (phone);
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);
