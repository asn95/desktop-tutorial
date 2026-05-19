-- C3MR Database Schema (Supabase PostgreSQL)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types for status and roles
CREATE TYPE user_role AS ENUM ('manager', 'officer');
CREATE TYPE target_status AS ENUM ('pending', 'in_progress', 'completed');
CREATE TYPE payment_status_enum AS ENUM ('Promise to Pay', 'Paid', 'Refused', 'Not Home', 'Partial Payment');

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id TEXT UNIQUE,
    name TEXT NOT NULL,
    role user_role DEFAULT 'officer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Targets Table
CREATE TABLE IF NOT EXISTS targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    amount_due DECIMAL(12, 2) NOT NULL,
    assigned_officer UUID REFERENCES users(id),
    status target_status DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_id UUID REFERENCES targets(id) NOT NULL,
    officer_id UUID REFERENCES users(id) NOT NULL,
    payment_status payment_status_enum NOT NULL,
    notes TEXT,
    photo_url TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Upload Batches Table (For tracking CSV uploads)
CREATE TABLE IF NOT EXISTS upload_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_name TEXT NOT NULL,
    total_rows INTEGER NOT NULL,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
