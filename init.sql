-- PostgreSQL Initialization Script for A-05 RAG Pipeline

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Create basic tables will be created by SQLModel, but we can verify the extension is working
-- Test vector functionality
SELECT '[1,2,3]'::vector;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE samantha_db TO samantha_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO samantha_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO samantha_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO samantha_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO samantha_user;
