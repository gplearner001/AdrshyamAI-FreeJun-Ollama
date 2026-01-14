-- Run this against your PostgreSQL database once
ALTER TABLE conversational_prompts
ADD COLUMN IF NOT EXISTS greeting_message TEXT;
