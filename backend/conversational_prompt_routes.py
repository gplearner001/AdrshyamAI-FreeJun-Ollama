#!/usr/bin/env python3
"""
Conversational Prompt API Routes
Handles CRUD operations for conversational prompts used in AI voice conversations.
Uses PostgreSQL for storage.
"""

import os
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor
import psycopg2
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["conversational_prompts"])

class ConversationalPromptCreate(BaseModel):
    name: str
    system_prompt: str
    user_id: str
    is_active: bool = False

class ConversationalPromptUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None

class PromptService:
    """Service for managing conversational prompts in PostgreSQL"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.connection = None
        self._ensure_connection()
        self._initialize_schema()

    def _ensure_connection(self):
        """Ensure database connection is established"""
        if not self.database_url:
            logger.warning("DATABASE_URL not configured")
            return False

        try:
            if not self.connection or self.connection.closed:
                self.connection = psycopg2.connect(self.database_url)
                logger.info("Database connection established for prompt service")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.connection = None
            return False

    def _initialize_schema(self):
        """Initialize database schema for conversational prompts"""
        if not self._ensure_connection():
            return

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversational_prompts (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name TEXT NOT NULL,
                        system_prompt TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT false,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );

                    CREATE INDEX IF NOT EXISTS idx_prompts_user_id
                    ON conversational_prompts(user_id);

                    CREATE INDEX IF NOT EXISTS idx_prompts_active
                    ON conversational_prompts(is_active);

                    CREATE UNIQUE INDEX IF NOT EXISTS idx_prompts_user_active
                    ON conversational_prompts(user_id)
                    WHERE is_active = true;
                """)
                self.connection.commit()
                logger.info("Conversational prompts schema initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            if self.connection:
                self.connection.rollback()

    def is_available(self) -> bool:
        """Check if database service is available"""
        return self._ensure_connection()

    def get_connection(self):
        """Get database connection"""
        if not self._ensure_connection():
            raise Exception("Database not available")
        return self.connection

prompt_service = PromptService()

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_prompt(prompt: ConversationalPromptCreate):
    """Create a new conversational prompt"""
    if not prompt_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Database service not available"
        )

    try:
        conn = prompt_service.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if prompt.is_active:
            cur.execute("""
                UPDATE conversational_prompts
                SET is_active = false, updated_at = NOW()
                WHERE user_id = %s AND is_active = true
            """, (prompt.user_id,))

        cur.execute("""
            INSERT INTO conversational_prompts (name, system_prompt, user_id, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, system_prompt, user_id, is_active, created_at, updated_at
        """, (prompt.name, prompt.system_prompt, prompt.user_id, prompt.is_active))

        created_prompt = cur.fetchone()
        conn.commit()

        if not created_prompt:
            raise HTTPException(
                status_code=500,
                detail="Failed to create prompt"
            )

        return {
            'success': True,
            'data': dict(created_prompt),
            'message': 'Prompt created successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating prompt: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create prompt: {str(e)}"
        )

@router.get("")
async def get_prompts(user_id: str):
    """Get all conversational prompts for a user"""
    if not prompt_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Database service not available"
        )

    try:
        conn = prompt_service.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, name, system_prompt, user_id, is_active, created_at, updated_at
            FROM conversational_prompts
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

        prompts = cur.fetchall()

        return {
            'success': True,
            'data': [dict(row) for row in prompts],
            'count': len(prompts)
        }

    except Exception as e:
        logger.error(f"Error fetching prompts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch prompts: {str(e)}"
        )

@router.put("/{prompt_id}")
async def update_prompt(prompt_id: str, update_data: ConversationalPromptUpdate):
    """Update an existing conversational prompt"""
    if not prompt_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Database service not available"
        )

    try:
        conn = prompt_service.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Build dynamic update query
        update_fields = []
        params = []

        if update_data.name is not None:
            update_fields.append("name = %s")
            params.append(update_data.name)

        if update_data.system_prompt is not None:
            update_fields.append("system_prompt = %s")
            params.append(update_data.system_prompt)

        if not update_fields:
            raise HTTPException(
                status_code=400,
                detail="No fields to update"
            )

        update_fields.append("updated_at = NOW()")
        params.append(prompt_id)

        query = f"""
            UPDATE conversational_prompts
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, name, system_prompt, user_id, is_active, created_at, updated_at
        """

        cur.execute(query, params)
        updated_prompt = cur.fetchone()
        conn.commit()

        if not updated_prompt:
            raise HTTPException(
                status_code=404,
                detail="Prompt not found"
            )

        return {
            'success': True,
            'data': dict(updated_prompt),
            'message': 'Prompt updated successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating prompt: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update prompt: {str(e)}"
        )

@router.post("/{prompt_id}/activate")
async def activate_prompt(prompt_id: str):
    """Set a prompt as active and deactivate all other prompts for the same user"""
    if not prompt_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Database service not available"
        )

    try:
        conn = prompt_service.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # First, get the prompt to check if it exists and get the user_id
        cur.execute("""
            SELECT id, user_id, name
            FROM conversational_prompts
            WHERE id = %s
        """, (prompt_id,))

        prompt = cur.fetchone()

        if not prompt:
            raise HTTPException(
                status_code=404,
                detail="Prompt not found"
            )

        user_id = prompt['user_id']

        # Deactivate all prompts for this user
        cur.execute("""
            UPDATE conversational_prompts
            SET is_active = false, updated_at = NOW()
            WHERE user_id = %s AND is_active = true
        """, (user_id,))

        # Activate the specified prompt
        cur.execute("""
            UPDATE conversational_prompts
            SET is_active = true, updated_at = NOW()
            WHERE id = %s
            RETURNING id, name, system_prompt, user_id, is_active, created_at, updated_at
        """, (prompt_id,))

        activated_prompt = cur.fetchone()
        conn.commit()

        logger.info(f"Activated prompt '{prompt['name']}' (ID: {prompt_id}) for user {user_id}")

        return {
            'success': True,
            'data': dict(activated_prompt),
            'message': 'Prompt activated successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error activating prompt: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate prompt: {str(e)}"
        )

@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a conversational prompt"""
    if not prompt_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Database service not available"
        )

    try:
        conn = prompt_service.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            DELETE FROM conversational_prompts
            WHERE id = %s
            RETURNING id, name
        """, (prompt_id,))

        deleted_prompt = cur.fetchone()
        conn.commit()

        if not deleted_prompt:
            raise HTTPException(
                status_code=404,
                detail="Prompt not found"
            )

        logger.info(f"Deleted prompt '{deleted_prompt['name']}' (ID: {prompt_id})")

        return {
            'success': True,
            'message': 'Prompt deleted successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting prompt: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete prompt: {str(e)}"
        )
