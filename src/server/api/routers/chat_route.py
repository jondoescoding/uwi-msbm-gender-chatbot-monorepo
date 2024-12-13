from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ...core.logging import setup_logger
from server.service.chat_service import ChatService

router = APIRouter()
logger = setup_logger(name=__name__)

# Initialize service
chat_service = ChatService()

# Define request/response models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    conversation_id: str

@router.post("")
async def chat(request: ChatRequest):
    """Process a chat request and return a response"""
    try:
        logger.info("🟨 [API] Received chat request")
        logger.info(f"🟨 [API] Number of messages: {len(request.messages)}")
        logger.info(f"🟨 [API] Conversation ID: {request.conversation_id}")
        
        # Log the last message content
        if request.messages:
            logger.info(f"🟨 [API] Latest message: {request.messages[-1].content}")
        
        # Convert messages to dict format
        messages = [msg.model_dump() for msg in request.messages]
        logger.info("🟨 [API] Converted messages to dict format")
        
        # Process request using service
        logger.info("🟨 [API] Forwarding request to ChatService")
        response = await chat_service.process_chat_request(
            messages=messages,
            conversation_id=request.conversation_id
        )
        logger.info("🟨 [API] Received response from ChatService")
        
        # Log response summary
        logger.info(f"🟨 [API] Response length: {len(response['response'])}")
        logger.info(f"🟨 [API] Number of sources: {len(response['sources'])}")
        
        return ChatResponse(**response)
        
    except Exception as e:
        logger.error(f"🔴 [API] Chat error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
