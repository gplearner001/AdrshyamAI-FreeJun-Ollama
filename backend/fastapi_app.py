#!/usr/bin/env python3
"""
FastAPI application for Teler WebSocket streaming
Replaces Flask with FastAPI for better WebSocket support
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from websocket_handler import websocket_handler
from ollama_service import ollama_service
from sarvam_service import sarvam_service
from vad_processor import vad_processor
from knowledge_base_routes import router as kb_router
from rag_service import rag_service
from database_service import database_service
from webhook_service import webhook_service

# Teler imports
try:
    from teler import AsyncClient, CallFlow
    TELER_AVAILABLE = True
except ImportError:
    TELER_AVAILABLE = False

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="AdrshyamAI Call Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include knowledge base router
app.include_router(kb_router)

# Configuration
TELER_API_KEY = os.getenv('TELER_API_KEY', 'cf771fc46a1fddb7939efa742801de98e48b0826be4d8b9976d3c7374a02368b')
BACKEND_DOMAIN = os.getenv('BACKEND_DOMAIN', 'localhost:8000')
BACKEND_URL = f"https://{BACKEND_DOMAIN}" if not BACKEND_DOMAIN.startswith('localhost') else f"http://{BACKEND_DOMAIN}"

# In-memory storage for call history
call_history = []

# Pydantic models
class CallFlowRequest(BaseModel):
    call_id: str
    account_id: str
    from_number: str
    to_number: str

class CallInitiateRequest(BaseModel):
    from_number: str
    to_number: str
    flow_url: str
    status_callback_url: Optional[str] = None
    record: bool = True
    knowledge_base_id: Optional[str] = None

# Mock Teler client for development
class MockTelerClient:
    """Mock teler client for development and testing."""
    
    async def create_call(self, **kwargs):
        """Mock call creation."""
        logger.info(f"Mock create_call called with: {kwargs}")
        return {
            'call_id': f"call_{int(datetime.now().timestamp())}",
            'status': 'initiated',
            'message': 'Call initiated successfully (mock)',
            'from_number': kwargs.get('from_number'),
            'to_number': kwargs.get('to_number'),
            'flow_url': kwargs.get('flow_url'),
            'record': kwargs.get('record', False)
        }

async def create_teler_call(from_number, to_number, flow_url, status_callback_url=None, record=True):
    """Create a call using the teler AsyncClient."""
    try:
        if TELER_AVAILABLE:
            logger.info(f"Creating call with teler AsyncClient")
            
            async with AsyncClient(api_key=TELER_API_KEY, timeout=30) as client:
                call_params = {
                    "from_number": from_number,
                    "to_number": to_number,
                    "flow_url": flow_url,
                    "record": record
                }
                
                if status_callback_url:
                    call_params["status_callback_url"] = status_callback_url
                
                logger.info(f"Call parameters: {call_params}")
                call = await client.calls.create(**call_params)
                
                call_response = {
                    'call_id': getattr(call, 'call_id', getattr(call, 'sid', f"call_{int(datetime.now().timestamp())}")),
                    'status': getattr(call, 'status', 'initiated'),
                    'from_number': from_number,
                    'to_number': to_number,
                    'flow_url': flow_url,
                    'record': record,
                    'message': 'Call initiated successfully'
                }
                
                return call_response
        else:
            logger.info("Using mock client for call creation")
            mock_client = MockTelerClient()
            return await mock_client.create_call(
                from_number=from_number,
                to_number=to_number,
                flow_url=flow_url,
                status_callback_url=status_callback_url,
                record=record
            )
    except Exception as e:
        logger.error(f"Error creating call: {str(e)}")
        mock_client = MockTelerClient()
        return await mock_client.create_call(
            from_number=from_number,
            to_number=to_number,
            flow_url=flow_url,
            status_callback_url=status_callback_url,
            record=record
        )

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        'status': 'OK',
        'message': 'Teler FastAPI Service is running',
        'timestamp': datetime.now().isoformat(),
        'teler_available': TELER_AVAILABLE,
        'ollama_available': ollama_service.is_available(),
        'sarvam_available': sarvam_service.is_available()
    }

@app.post("/flow", status_code=status.HTTP_200_OK)
async def stream_flow(payload: CallFlowRequest):
    """
    Build and return Stream flow for Teler.
    This endpoint is called by Teler when a call is answered.
    """
    logger.info(f"Flow endpoint called with: {payload}")
    
    # Create stream flow configuration
    stream_flow = CallFlow.stream(
        ws_url=f"wss://{BACKEND_DOMAIN}/media-stream",
        chunk_size=2000,
        record=True
    )
    
    logger.info(f"Generated stream flow: {stream_flow}")
    return JSONResponse(stream_flow)

@app.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook_receiver(data: dict = Body(...)):
    """Handle webhook callbacks from Teler."""
    logger.info(f"--------Webhook Payload-------- {data}")
    
    # Handle call completion events
    event = data.get('event')
    if event in ['call.completed', 'stream.completed']:
        call_id = data.get('data', {}).get('call_id')
        if call_id:
            # Find and mark WebSocket connections as ended
            for connection_id, metadata in websocket_handler.stream_metadata.items():
                if metadata.get('call_id') == call_id:
                    logger.info(f"Marking call as ended for connection: {connection_id}")
                    if connection_id in websocket_handler.call_states:
                        websocket_handler.call_states[connection_id]['call_ended'] = True
                        websocket_handler.call_states[connection_id]['status'] = 'completed'
                        websocket_handler.call_states[connection_id]['is_processing'] = False
                    
                    # Cancel any ongoing silence monitoring
                    if connection_id in websocket_handler.silence_timers:
                        websocket_handler.silence_timers[connection_id].cancel()
                        del websocket_handler.silence_timers[connection_id]
                    
                    # Clear audio buffer to prevent further processing
                    if connection_id in websocket_handler.audio_buffers:
                        websocket_handler.audio_buffers[connection_id].clear()
                        logger.info(f"🧹 Cleared audio buffer for ended call: {connection_id}")
    
    # Update call history with webhook data
    call_id = data.get('call_id') or data.get('CallSid') or data.get('id') or data.get('data', {}).get('call_id')
    if call_id:
        for call in call_history:
            if call.get('call_id') == call_id:
                call['webhook_data'] = data
                call['status'] = data.get('status') or data.get('data', {}).get('status', call['status'])
                call['updated_at'] = datetime.now().isoformat()
                if event == 'call.completed':
                    call['status'] = 'completed'
                    call['end_time'] = data.get('data', {}).get('hangup_time')
                    call['duration'] = data.get('data', {}).get('duration')
                break
    
    return JSONResponse(content={"message": "Webhook received successfully"})

@app.post("/api/calls/initiate")
async def initiate_call(request: CallInitiateRequest):
    """Initiate a new call using the teler library."""
    try:
        logger.info(f"Initiating call from {request.from_number} to {request.to_number}")
        
        status_callback_url = request.status_callback_url or f"{BACKEND_URL}/webhook"
        
        # Create the call using async teler client
        call_response = await create_teler_call(
            from_number=request.from_number,
            to_number=request.to_number,
            flow_url=request.flow_url,
            status_callback_url=status_callback_url,
            record=request.record
        )
        
        # Create call record
        call_record = {
            'id': len(call_history) + 1,
            'call_id': call_response['call_id'],
            'status': call_response['status'],
            'from_number': request.from_number,
            'to_number': request.to_number,
            'flow_url': request.flow_url,
            'status_callback_url': status_callback_url,
            'record': request.record,
            'knowledge_base_id': request.knowledge_base_id,
            'timestamp': datetime.now().isoformat(),
            'response_data': call_response,
            'call_type': 'conversation',
            'notes': 'Configured for bidirectional phone conversation with WebSocket streaming'
        }
        
        # Store in history
        call_history.insert(0, call_record)

        logger.info(f"✅ Call initiated successfully: {call_response['call_id']}")
        if request.knowledge_base_id:
            logger.info(f"📚 Knowledge base '{request.knowledge_base_id}' associated with call '{call_response['call_id']}'")
        
        return {
            'success': True,
            'data': {
                'call_id': call_response['call_id'],
                'status': call_response['status'],
                'from_number': request.from_number,
                'to_number': request.to_number,
                'flow_url': request.flow_url,
                'record': request.record,
                'knowledge_base_id': request.knowledge_base_id,
                'timestamp': call_record['timestamp'],
                'call_type': 'conversation',
                'message': 'Call configured for WebSocket streaming conversation'
            },
            'message': 'Call initiated successfully - configured for WebSocket streaming'
        }
        
    except Exception as e:
        logger.error(f"Error in initiate_call: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate call: {str(e)}"
        )

@app.get("/api/calls/history")
async def get_call_history():
    """Get call history."""
    return {
        'success': True,
        'data': call_history,
        'count': len(call_history)
    }

@app.get("/api/calls/active")
async def get_active_calls():
    """Get currently active calls from WebSocket streams."""
    active_streams = websocket_handler.get_active_streams()
    active_calls = []
    
    for connection_id, stream_info in active_streams.items():
        active_calls.append({
            'call_id': stream_info.get('call_id'),
            'stream_id': stream_info.get('stream_id'),
            'connection_id': connection_id,
            'from': stream_info.get('from_number', 'Unknown'),
            'to': stream_info.get('to_number', 'Unknown'),
            'status': 'active',
            'started_at': stream_info.get('started_at'),
            'encoding': stream_info.get('encoding'),
            'sample_rate': stream_info.get('sample_rate')
        })
    
    return {
        'success': True,
        'data': active_calls,
        'count': len(active_calls)
    }

@app.get("/api/calls/{call_id}")
async def get_call_details(call_id: str):
    """Get details for a specific call."""
    call = next((c for c in call_history if c['call_id'] == call_id), None)
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        'success': True,
        'data': call
    }

@app.post("/api/ai/conversation")
async def ai_conversation(data: dict = Body(...)):
    """Generate AI conversation responses using Ollama."""
    if not ollama_service.is_available():
        raise HTTPException(status_code=503, detail="Ollama LLM service not available")

    conversation_context = {
        'history': data.get('history', []),
        'current_input': data.get('current_input', ''),
        'call_id': data.get('call_id', ''),
        'context': data.get('context', {}),
        'knowledge_base_id': data.get('knowledge_base_id')
    }

    try:
        response_text = await ollama_service.generate_conversation_response(conversation_context)

        return {
            'success': True,
            'data': {
                'response': response_text,
                'timestamp': datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error in AI conversation endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate AI response: {str(e)}")

@app.get("/api/ai/status")
async def ai_status():
    """Check AI service status."""
    return {
        'success': True,
        'data': {
            'ollama_available': ollama_service.is_available(),
            'service': 'Ollama LLM',
            'model': ollama_service.model if ollama_service.is_available() else None,
            'api_url': ollama_service.api_url
        }
    }

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """
    Handle WebSocket connection for Teler media streaming.
    This endpoint receives audio from Teler and can send audio back.
    """
    connection_id = None
    try:
        # Accept the WebSocket connection
        connection_id = await websocket_handler.connect(websocket)
        logger.info(f"Media stream WebSocket connected: {connection_id}")
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from Teler
                message = await websocket.receive_text()
                #logger.info(f"Received message: {message}")
                logger.debug(f"Received message: {message[:100]}...")
                
                # Handle the message
                await websocket_handler.handle_incoming_message(websocket, message, connection_id)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                # Send error message back to client
                error_response = {
                    "type": "error",
                    "message": str(e)
                }
                try:
                    await websocket.send_text(json.dumps(error_response))
                except:
                    break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if connection_id:
            websocket_handler.disconnect(connection_id)

# Additional WebSocket control endpoints
@app.post("/api/websocket/interrupt/{connection_id}")
async def send_interrupt(connection_id: str, chunk_id: int = Body(...)):
    """Send interrupt message to specific WebSocket connection."""
    await websocket_handler.send_interrupt(connection_id, chunk_id)
    return {"message": f"Interrupt sent for chunk {chunk_id}"}

@app.post("/api/websocket/clear/{connection_id}")
async def send_clear(connection_id: str):
    """Send clear message to specific WebSocket connection."""
    await websocket_handler.send_clear(connection_id)
    return {"message": "Clear message sent"}

@app.get("/api/websocket/streams")
async def get_websocket_streams():
    """Get information about active WebSocket streams."""
    streams = websocket_handler.get_active_streams()
    return {
        'success': True,
        'data': streams,
        'count': len(streams)
    }

@app.post("/api/calls/associate-kb")
async def associate_knowledge_base(data: dict = Body(...)):
    """
    Associate a knowledge base with a call.
    Used by AdrshyamAI Audio Client to link KB with direct WebSocket connections.
    """
    try:
        call_id = data.get('call_id')
        knowledge_base_id = data.get('knowledge_base_id')

        if not call_id:
            raise HTTPException(status_code=400, detail="call_id is required")

        # Check if call already exists in history (from initiate_call)
        existing_call = None
        for call in call_history:
            if call.get('call_id') == call_id:
                existing_call = call
                break

        if existing_call:
            # Update existing call record with knowledge base
            existing_call['knowledge_base_id'] = knowledge_base_id
            existing_call['updated_at'] = datetime.now().isoformat()
            logger.info(f"📚 Updated existing call '{call_id}' with knowledge base '{knowledge_base_id}'")
        else:
            # Store new call record for WebSocket connections
            call_record = {
                'id': len(call_history) + 1,
                'call_id': call_id,
                'status': 'active',
                'from_number': 'WebSocket Client',
                'to_number': 'AI Assistant',
                'flow_url': 'WebSocket Direct',
                'knowledge_base_id': knowledge_base_id,
                'timestamp': datetime.now().isoformat(),
                'call_type': 'websocket',
                'notes': 'AdrshyamAI Audio Client connection'
            }

            call_history.insert(0, call_record)
            logger.info(f"📚 Associated knowledge base '{knowledge_base_id}' with new call '{call_id}'")

        return {
            'success': True,
            'message': 'Knowledge base associated with call',
            'data': {
                'call_id': call_id,
                'knowledge_base_id': knowledge_base_id
            }
        }
    except Exception as e:
        logger.error(f"Error associating knowledge base: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to associate knowledge base: {str(e)}"
        )

@app.get("/api/calls/debug")
async def debug_call_history():
    """Debug endpoint to view call history and knowledge base associations."""
    return {
        'success': True,
        'data': {
            'call_history': call_history,
            'count': len(call_history)
        }
    }

@app.get("/api/transcripts/{call_id}")
async def get_transcript(call_id: str):
    """Get call transcript by call_id from database."""
    if not database_service.is_available():
        raise HTTPException(status_code=503, detail="Database service not available")

    transcript = database_service.get_call_transcript(call_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    return {
        'success': True,
        'data': transcript
    }

@app.get("/api/transcripts")
async def get_transcripts(limit: int = 50):
    """Get recent call transcripts from database."""
    if not database_service.is_available():
        raise HTTPException(status_code=503, detail="Database service not available")

    transcripts = database_service.get_recent_transcripts(limit)
    return {
        'success': True,
        'data': transcripts,
        'count': len(transcripts)
    }

@app.get("/api/webhook/config")
async def get_webhook_config():
    """Get current webhook configuration."""
    return {
        'success': True,
        'data': {
            'webhook_url': webhook_service.get_webhook_url(),
            'is_configured': webhook_service.is_configured()
        }
    }

class WebhookConfigRequest(BaseModel):
    webhook_url: str

@app.post("/api/webhook/config")
async def update_webhook_config(request: WebhookConfigRequest):
    """Update webhook configuration."""
    webhook_service.update_webhook_url(request.webhook_url)
    return {
        'success': True,
        'message': 'Webhook configuration updated',
        'data': {
            'webhook_url': webhook_service.get_webhook_url(),
            'is_configured': webhook_service.is_configured()
        }
    }

@app.post("/api/webhook/retry/{call_id}")
async def retry_webhook(call_id: str):
    """Retry sending transcript to webhook for a specific call."""
    if not database_service.is_available():
        raise HTTPException(status_code=503, detail="Database service not available")

    if not webhook_service.is_configured():
        raise HTTPException(status_code=400, detail="Webhook not configured")

    transcript = database_service.get_call_transcript(call_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    success = await webhook_service.send_transcript(
        call_id=call_id,
        conversation=transcript.get('conversation', []),
        metadata=transcript.get('metadata', {})
    )

    if success:
        database_service.mark_webhook_sent(call_id)
        return {
            'success': True,
            'message': 'Transcript sent to webhook successfully'
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to send transcript to webhook")

@app.get("/api/webhook/pending")
async def get_pending_webhooks():
    """Get transcripts pending webhook delivery."""
    if not database_service.is_available():
        raise HTTPException(status_code=503, detail="Database service not available")

    pending = database_service.get_pending_webhook_transcripts()
    return {
        'success': True,
        'data': pending,
        'count': len(pending)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    
    logger.info(f"Starting Teler FastAPI Service on port {port}")
    logger.info(f"Teler library available: {TELER_AVAILABLE}")
    logger.info(f"Environment variables loaded:")
    logger.info(f"  - OLLAMA_API_URL: {os.getenv('OLLAMA_API_URL', 'https://ebf431ea9bc8.ngrok-free.app')}")
    logger.info(f"  - OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL', 'llama3.2')}")
    logger.info(f"  - SARVAM_API_KEY: {'***' + os.getenv('SARVAM_API_KEY', 'NOT_SET')[-4:] if os.getenv('SARVAM_API_KEY') else 'NOT_SET'}")
    logger.info(f"  - VOYAGE_API_KEY: {'***' + os.getenv('VOYAGE_API_KEY', 'NOT_SET')[-4:] if os.getenv('VOYAGE_API_KEY') else 'NOT_SET'}")
    logger.info(f"Ollama LLM available: {ollama_service.is_available()}")
    logger.info(f"Sarvam AI available: {sarvam_service.is_available()}")
    logger.info(f"RAG Service available: {rag_service.is_available()}")
    logger.info(f"WebRTC VAD available: {vad_processor is not None}")
    logger.info(f"Database service available: {database_service.is_available()}")
    logger.info(f"Webhook configured: {webhook_service.is_configured()}")
    if webhook_service.is_configured():
        logger.info(f"Webhook URL: {webhook_service.get_webhook_url()}")

    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv('ENVIRONMENT') == 'development'
    )