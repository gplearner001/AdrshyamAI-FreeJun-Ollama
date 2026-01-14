#!/usr/bin/env python3
"""
Database service for PostgreSQL operations
Handles call transcript logging and storage
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for managing PostgreSQL database operations"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.connection = None
        self._ensure_connection()
        self._initialize_schema()

    def _ensure_connection(self):
        """Ensure database connection is established"""
        if not self.database_url:
            logger.warning("DATABASE_URL not configured, database operations will be skipped")
            return False

        try:
            if not self.connection or self.connection.closed:
                self.connection = psycopg2.connect(self.database_url)
                logger.info("Database connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.connection = None
            return False

    def _initialize_schema(self):
        """Initialize database schema for call transcripts and AI configurations"""
        if not self._ensure_connection():
            return

        try:
            with self.connection.cursor() as cursor:
                # Call Transcripts Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS call_transcripts (
                        id SERIAL PRIMARY KEY,
                        call_id VARCHAR(255) UNIQUE NOT NULL,
                        connection_id VARCHAR(255),
                        call_type VARCHAR(50),
                        status VARCHAR(50),
                        from_number VARCHAR(50),
                        to_number VARCHAR(50),
                        language VARCHAR(10),
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        duration_seconds INTEGER,
                        conversation JSONB,
                        metadata JSONB,
                        knowledge_base_id VARCHAR(255),
                        webhook_sent BOOLEAN DEFAULT FALSE,
                        webhook_sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_call_id ON call_transcripts(call_id);
                    CREATE INDEX IF NOT EXISTS idx_created_at ON call_transcripts(created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_webhook_sent ON call_transcripts(webhook_sent);
                """)

                # AI Configurations Table
                cursor.execute("""
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
                """)

                self.connection.commit()
                logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            self.connection.rollback()

    def save_call_transcript(
        self,
        call_id: str,
        connection_id: str,
        conversation: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
        call_state: Optional[Dict[str, Any]] = None,
        stream_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save call transcript to database

        Args:
            call_id: Unique call identifier
            connection_id: WebSocket connection identifier
            conversation: List of conversation messages
            metadata: Additional metadata about the call
            call_state: Call state information
            stream_metadata: Stream metadata information

        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_connection():
            logger.warning("Database not available, skipping transcript save")
            return False

        try:
            # Extract information from parameters
            call_type = metadata.get('call_type', 'unknown') if metadata else 'unknown'
            status = call_state.get('status', 'completed') if call_state else 'completed'
            language = call_state.get('current_language', 'en-IN') if call_state else 'en-IN'
            knowledge_base_id = call_state.get('knowledge_base_id') if call_state else None

            # Calculate call duration
            start_time = metadata.get('start_time') if metadata else None
            end_time = datetime.now()
            duration_seconds = None

            if start_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                duration_seconds = int((end_time - start_time).total_seconds())

            # Prepare metadata - convert datetime objects to ISO strings for JSON serialization
            def serialize_datetime(obj):
                """Convert datetime objects to ISO format strings"""
                if isinstance(obj, dict):
                    return {k: serialize_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_datetime(item) for item in obj]
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                return obj

            full_metadata = {
                **(metadata or {}),
                **(stream_metadata or {}),
                'call_state': call_state
            }

            # Serialize all datetime objects in metadata
            full_metadata = serialize_datetime(full_metadata)

            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO call_transcripts (
                        call_id, connection_id, call_type, status,
                        from_number, to_number, language,
                        start_time, end_time, duration_seconds,
                        conversation, metadata, knowledge_base_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (call_id) DO UPDATE SET
                        conversation = EXCLUDED.conversation,
                        metadata = EXCLUDED.metadata,
                        end_time = EXCLUDED.end_time,
                        duration_seconds = EXCLUDED.duration_seconds,
                        status = EXCLUDED.status,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    call_id,
                    connection_id,
                    call_type,
                    status,
                    stream_metadata.get('from_number') if stream_metadata else None,
                    stream_metadata.get('to_number') if stream_metadata else None,
                    language,
                    start_time,
                    end_time,
                    duration_seconds,
                    json.dumps(conversation),
                    json.dumps(full_metadata),
                    knowledge_base_id
                ))
                self.connection.commit()
                logger.info(f"Successfully saved call transcript for call_id: {call_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to save call transcript: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def get_call_transcript(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve call transcript by call_id

        Args:
            call_id: Call identifier

        Returns:
            Call transcript data or None if not found
        """
        if not self._ensure_connection():
            return None

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM call_transcripts
                    WHERE call_id = %s
                """, (call_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to retrieve call transcript: {e}")
            return None

    def get_pending_webhook_transcripts(self) -> List[Dict[str, Any]]:
        """
        Get all transcripts that haven't been sent to webhook yet

        Returns:
            List of call transcripts pending webhook delivery
        """
        if not self._ensure_connection():
            return []

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM call_transcripts
                    WHERE webhook_sent = FALSE
                    ORDER BY created_at ASC
                """)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to retrieve pending webhook transcripts: {e}")
            return []

    def mark_webhook_sent(self, call_id: str) -> bool:
        """
        Mark a transcript as sent to webhook

        Args:
            call_id: Call identifier

        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_connection():
            return False

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE call_transcripts
                    SET webhook_sent = TRUE,
                        webhook_sent_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE call_id = %s
                """, (call_id,))
                self.connection.commit()
                logger.info(f"Marked transcript as webhook sent for call_id: {call_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to mark webhook sent: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def get_recent_transcripts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent call transcripts

        Args:
            limit: Maximum number of transcripts to return

        Returns:
            List of recent call transcripts
        """
        if not self._ensure_connection():
            return []

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM call_transcripts
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to retrieve recent transcripts: {e}")
            return []

    def save_ai_config(
        self,
        selected_llm_service: str,
        ollama_model: Optional[str] = None,
        claude_model: Optional[str] = None,
        config_name: str = 'default_ai_config'
    ) -> bool:
        """
        Save or update AI configuration.

        Args:
            selected_llm_service: The currently selected LLM service ('ollama' or 'claude').
            ollama_model: Optional override for Ollama model.
            claude_model: Optional override for Claude model.
            config_name: Name of the configuration (defaults to 'default_ai_config').

        Returns:
            True if successful, False otherwise.
        """
        if not self._ensure_connection():
            logger.warning("Database not available, skipping AI config save")
            return False

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ai_configurations (config_name, selected_llm_service, ollama_model, claude_model)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (config_name) DO UPDATE SET
                        selected_llm_service = EXCLUDED.selected_llm_service,
                        ollama_model = EXCLUDED.ollama_model,
                        claude_model = EXCLUDED.claude_model,
                        updated_at = CURRENT_TIMESTAMP
                """, (config_name, selected_llm_service, ollama_model, claude_model))
                self.connection.commit()
                logger.info(f"Successfully saved AI configuration for '{config_name}'")
                return True
        except Exception as e:
            logger.error(f"Failed to save AI configuration: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def get_ai_config(self, config_name: str = 'default_ai_config') -> Optional[Dict[str, Any]]:
        """
        Retrieve AI configuration by name.

        Args:
            config_name: Name of the configuration (defaults to 'default_ai_config').

        Returns:
            AI configuration data or None if not found.
        """
        if not self._ensure_connection():
            return None

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT selected_llm_service, ollama_model, claude_model
                    FROM ai_configurations
                    WHERE config_name = %s
                """, (config_name,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to retrieve AI configuration: {e}")
            return None

    def is_available(self) -> bool:
        """Check if database service is available"""
        return self._ensure_connection()

    def close(self):
        """Close database connection"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Database connection closed")

database_service = DatabaseService()
