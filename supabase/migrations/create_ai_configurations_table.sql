/*
  # Create ai_configurations table
  1. New Tables: ai_configurations (id serial, config_name text, selected_llm_service text, ollama_model text, claude_model text)
  2. Security: Enable RLS, add policies for authenticated users (read/write)
*/
CREATE TABLE IF NOT EXISTS ai_configurations (
    id SERIAL PRIMARY KEY,
    config_name TEXT UNIQUE NOT NULL DEFAULT 'default_ai_config',
    selected_llm_service TEXT NOT NULL DEFAULT 'ollama', -- 'ollama' or 'claude'
    ollama_model TEXT, -- specific ollama model to use, if different from .env
    claude_model TEXT, -- specific claude model to use, if different from .env
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Ensure only one default config exists
INSERT INTO ai_configurations (config_name, selected_llm_service)
VALUES ('default_ai_config', 'ollama')
ON CONFLICT (config_name) DO NOTHING;

-- Note: RLS policies are typically managed within Supabase's dashboard.
-- Since we are using raw PostgreSQL, these RLS statements are illustrative
-- and would need to be applied if you were using a system that supports them
-- directly on a raw PostgreSQL instance, or if you later connect this to Supabase.
-- For a pure PostgreSQL setup without Supabase, RLS might be managed at the application level.
-- ALTER TABLE ai_configurations ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Allow authenticated read access to AI configurations" ON ai_configurations
-- FOR SELECT TO authenticated
-- USING (true);
-- CREATE POLICY "Allow authenticated update access to AI configurations" ON ai_configurations
-- FOR UPDATE TO authenticated
-- USING (true) WITH CHECK (true);
-- CREATE POLICY "Allow authenticated insert access to AI configurations" ON ai_configurations
-- FOR INSERT TO authenticated
-- WITH CHECK (true);
