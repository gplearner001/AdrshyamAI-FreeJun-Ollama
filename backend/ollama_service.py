#!/usr/bin/env python3
"""
Ollama LLM Service for AdrshyamAI Call Service
Provides AI-powered call flow generation and conversation handling using Ollama.
"""

import os
import json
import logging
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class OllamaService:
    """Service for interacting with Ollama LLM API."""

    def __init__(self):
        self.api_url = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        self.available = False
        self.database_url = os.getenv('DATABASE_URL')

        logger.info(f"Ollama API URL: {self.api_url}")
        logger.info(f"Ollama Model: {self.model}")

        self._test_connection()

    # -------------------------------------------------------
    # 🧩 Fetch active conversational prompt from PostgreSQL
    # -------------------------------------------------------
    def _get_active_conversational_prompt(self, user_id: Optional[str] = None) -> Optional[str]:
        """Fetch active system prompt from PostgreSQL."""
        if not self.database_url:
            logger.warning("DATABASE_URL not configured for OllamaService")
            return None

        try:
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            if user_id:
                cur.execute("""
                    SELECT system_prompt FROM conversational_prompts
                    WHERE is_active = true AND user_id = %s
                    LIMIT 1
                """, (user_id,))
            else:
                cur.execute("""
                    SELECT system_prompt FROM conversational_prompts
                    WHERE is_active = true
                    ORDER BY updated_at DESC
                    LIMIT 1
                """)

            row = cur.fetchone()
            cur.close()
            conn.close()

            if row and row.get("system_prompt"):
                logger.info("✅ Active conversational prompt loaded from database")
                return row["system_prompt"]

            logger.info("ℹ️ No active conversational prompt found in database")
            return None

        except Exception as e:
            logger.error(f"Error fetching active conversational prompt: {e}")
            return None

    # -------------------------------------------------------
    # 🧪 Test Ollama Cloud Connection
    # -------------------------------------------------------
    def _test_connection(self):
        """Test connection to Ollama Cloud API."""
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.getenv("OLLAMA_API_KEY", "")}'
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "test"}],
                "stream": False
            }
            response = requests.post(
                f"{self.api_url}/api/chat",
                json=payload,
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                self.available = True
                logger.info(f"Ollama service initialized successfully with model: {self.model}")
            else:
                logger.warning(f"Ollama API returned status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to connect to Ollama API at {self.api_url}: {str(e)}")

    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        return self.available

    # -------------------------------------------------------
    # 🧠 Generate conversation response
    # -------------------------------------------------------
    async def generate_conversation_response(self, conversation_context: Dict[str, Any], model_override: Optional[str] = None) -> str:
        """Generate conversation response using Ollama."""
        if not self.is_available():
            return "Hello! How can I help you today?"

        try:
            from rag_service import rag_service

            knowledge_base_context = ""
            knowledge_base_id = conversation_context.get('knowledge_base_id')
            current_input = conversation_context.get('current_input', '')
            user_id = conversation_context.get('user_id')

            # ✅ Fetch active conversational prompt
            active_prompt = self._get_active_conversational_prompt(user_id=user_id)

            # Optional RAG (Knowledge Base) context
            if knowledge_base_id and current_input and rag_service.is_available():
                knowledge_base_context = await rag_service.get_context_for_query(
                    query=current_input,
                    knowledge_base_id=knowledge_base_id,
                    max_tokens=2000
                )

            # Build conversation prompt (with fallback)
            prompt = self._build_conversation_prompt(conversation_context, knowledge_base_context, active_prompt)

            # Generate completion
            response = self._generate_completion(prompt, temperature=0.7, max_tokens=500, model_override=model_override)
            return response.strip() if response else "I'm here. Please continue."

        except Exception as e:
            logger.error(f"Error generating conversation response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now."

    # -------------------------------------------------------
    # 🔧 Generate completion (send to Ollama)
    # -------------------------------------------------------
    def _generate_completion(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500, model_override: Optional[str] = None) -> str:
        """Generate completion using Ollama."""
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.getenv("OLLAMA_API_KEY", "")}'
            }
            payload = {
                "model": model_override or self.model, # Use override if provided
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "keep_alive": -1
            }
            response = requests.post(
                f"{self.api_url}/api/chat",
                json=payload,
                headers=headers,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                message = result.get('message', {})
                return message.get('content', '')
            else:
                logger.error(f"Ollama API error {response.status_code}: {response.text}")
                return ""

        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return ""

    # -------------------------------------------------------
    # 🧱 Build conversation prompt (DB + fallback)
    # -------------------------------------------------------
    def _build_conversation_prompt(
        self,
        conversation_context: Dict[str, Any],
        knowledge_base_context: str = "",
        db_system_prompt: Optional[str] = None
    ) -> str:
        """Build conversation prompt (use DB prompt if available)."""
        history = conversation_context.get('history', [])
        current_input = conversation_context.get('current_input', '')
        context = conversation_context.get('context', {})
        language = context.get('language', 'en-IN')
        language_name = self._get_language_name(language)

        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

        kb_instructions = ""
        if knowledge_base_context:
            kb_instructions = f"""
CRITICAL - KNOWLEDGE BASE CONTEXT:
{knowledge_base_context}
"""

        # ✅ Use DB system prompt if available
        if db_system_prompt:
            logger.info("💬 Using active conversational prompt from database")
            return f"""{db_system_prompt}

{kb_instructions}

Conversation history:
{history_text}

Current user input: {current_input}
"""

        # 🔁 Fallback to built-in prompt
        logger.info("⚙️ Using default built-in conversational prompt (no active DB prompt found)")
        return f"""You are an AI assistant in a voice call conversation in {language_name}.

IMPORTANT CONVERSATION RULES:
1. Keep responses SHORT (1-2 sentences maximum)
2. Respond naturally and conversationally in {language_name}
3. DO NOT ask multiple questions in one response
4. Wait for the user to speak - don't dominate the conversation
5. Be helpful but concise
6. ALWAYS respond in {language_name} language
7. If user says something brief or unclear, ask ONE clarifying question
8. Don't repeat the same type of response multiple times
{kb_instructions}

Conversation history:
{history_text}

Current user input: {current_input}

Provide a SHORT, helpful response that continues the conversation naturally.
Remember: This is a voice call - keep it brief and conversational!
"""

    # -------------------------------------------------------
    # 🧩 Default conversation/call flow configs (unchanged)
    # -------------------------------------------------------
    def _get_default_flow(self) -> Dict[str, Any]:
        """Get default call flow configuration."""
        return {
            "type": "stream",
            "greeting": "Hello! Thank you for calling. How can I assist you today?",
            "ws_url": f"wss://localhost:5000/media-stream",
            "chunk_size": 500,
            "record": True,
            "steps": [
                {"action": "speak", "text": "Hello! Thank you for calling. How can I assist you today?"},
                {"action": "listen", "timeout": 30},
                {"action": "respond", "type": "dynamic"}
            ]
        }

    def _get_conversation_flow(self) -> Dict[str, Any]:
        """Get conversation-focused call flow configuration."""
        return {
            "type": "conversation",
            "initial_message": "Hello! You're now connected. Please go ahead and speak.",
            "conversation_mode": "bidirectional",
            "keep_alive": True,
            "max_duration": 1800,
            "silence_timeout": 10,
            "end_call_phrases": ["goodbye", "end call", "hang up", "bye bye"],
            "steps": [
                {"action": "answer_call", "auto_answer": True},
                {"action": "play_greeting", "text": "Hello! You're now connected. Please go ahead and speak.", "voice": "natural"},
                {"action": "start_conversation", "mode": "continuous", "enable_interruption": True, "record_conversation": True},
                {"action": "monitor_silence", "timeout": 10, "prompt_text": "Are you still there? Please continue speaking."},
                {"action": "end_call_detection", "phrases": ["goodbye", "end call", "hang up", "bye bye"], "farewell_message": "Thank you for calling. Have a great day!"}
            ],
            "recording": {"enabled": True, "format": "wav", "quality": "high"},
            "audio_settings": {"echo_cancellation": True, "noise_reduction": True, "auto_gain_control": True}
        }

    def _get_language_name(self, language_code: str) -> str:
        """Get human-readable language name."""
        language_names = {
            'en-IN': 'English',
            'hi-IN': 'Hindi',
            'bn-IN': 'Bengali',
            'gu-IN': 'Gujarati',
            'kn-IN': 'Kannada',
            'ml-IN': 'Malayalam',
            'mr-IN': 'Marathi',
            'or-IN': 'Odia',
            'pa-IN': 'Punjabi',
            'ta-IN': 'Tamil',
            'te-IN': 'Telugu'
        }
        return language_names.get(language_code, 'Hindi/English mixed')

# -------------------------------------------------------
# 🌍 Global instance
# -------------------------------------------------------
ollama_service = OllamaService()
