#!/usr/bin/env python3
"""
Webhook service for sending call transcripts
Handles webhook delivery with retry logic
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class WebhookService:
    """Service for sending call transcripts to configured webhooks"""

    def __init__(self):
        self.webhook_url = os.getenv('WEBHOOK_URL', '').strip()
        self.timeout = 30
        self.max_retries = 3

    def is_configured(self) -> bool:
        """Check if webhook is configured"""
        return bool(self.webhook_url)

    async def send_transcript(
        self,
        call_id: str,
        conversation: list,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send call transcript to configured webhook

        Args:
            call_id: Call identifier
            conversation: List of conversation messages
            metadata: Additional metadata about the call

        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            logger.debug("Webhook URL not configured, skipping webhook delivery")
            return False

        payload = {
            'call_id': call_id,
            'conversation': conversation,
            'metadata': metadata or {},
            'timestamp': metadata.get('end_time') if metadata else None
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Sending transcript to webhook (attempt {attempt}/{self.max_retries})")
                logger.debug(f"Webhook URL: {self.webhook_url}")
                logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.webhook_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        headers={'Content-Type': 'application/json'}
                    ) as response:
                        if response.status in [200, 201, 202]:
                            logger.info(f"Successfully sent transcript to webhook for call_id: {call_id}")
                            response_text = await response.text()
                            logger.debug(f"Webhook response: {response_text}")
                            return True
                        else:
                            logger.warning(f"Webhook returned status {response.status}")
                            response_text = await response.text()
                            logger.warning(f"Response: {response_text}")

            except aiohttp.ClientError as e:
                logger.error(f"HTTP error sending to webhook (attempt {attempt}): {e}")
            except Exception as e:
                logger.error(f"Error sending to webhook (attempt {attempt}): {e}")

            if attempt < self.max_retries:
                logger.info(f"Retrying webhook delivery...")

        logger.error(f"Failed to send transcript to webhook after {self.max_retries} attempts")
        return False

    def update_webhook_url(self, webhook_url: str):
        """
        Update webhook URL dynamically

        Args:
            webhook_url: New webhook URL
        """
        self.webhook_url = webhook_url.strip()
        logger.info(f"Webhook URL updated: {self.webhook_url if self.webhook_url else '(not configured)'}")

    def get_webhook_url(self) -> str:
        """Get current webhook URL"""
        return self.webhook_url

webhook_service = WebhookService()
