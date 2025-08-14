"""
Conversation Orchestrator for WhatsApp Warmer
Manages conversation flow and generates messages using LiteLLM
"""

import logging
import random
import asyncio
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.connection import get_db
from warmer.models import WarmerSession, WarmerGroup, WarmerConversation, MessageType

logger = logging.getLogger(__name__)

# Check if litellm is available
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("LiteLLM not available. Install with: pip install litellm")


class ConversationOrchestrator:
    """Orchestrates conversations between warmer sessions"""
    
    def __init__(self, ollama_model: str = None, ollama_api_base: str = None):
        self.logger = logger
        
        # Determine which LLM provider to use
        self.llm_provider = os.getenv("LLM_PROVIDER", "groq").lower()
        
        if self.llm_provider == "groq":
            # Use Groq configuration
            model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
            self.model = f"groq/{model}"
            self.api_key = os.getenv("GROQ_API_KEY", "")
            self.api_base = None  # Not needed for Groq
            self.logger.info(f"Using Groq model: {model}")
        else:
            # Fallback to Ollama
            model = ollama_model or os.getenv("OLLAMA_MODEL", "gemma3:1b")
            self.model = f"ollama/{model}"
            self.api_base = ollama_api_base or os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
            self.api_key = None  # Not needed for Ollama
            self.logger.info(f"Using Ollama model: {model}")
        
        self.litellm_available = LITELLM_AVAILABLE
        
        # Conversation topics for variety
        self.conversation_topics = [
            "weekend plans",
            "favorite movies",
            "cooking recipes",
            "travel experiences",
            "sports events",
            "technology news",
            "book recommendations",
            "music preferences",
            "fitness routines",
            "local restaurants"
        ]
        
        # Fallback templates if LiteLLM is not available
        self.fallback_templates = {
            "greeting": [
                "Hey everyone! How's it going?",
                "Hi all! Hope you're having a great day",
                "Hello friends! What's everyone up to?",
                "Hey guys! How's everyone doing today?"
            ],
            "response": [
                "That sounds interesting!",
                "I totally agree with that",
                "Oh really? Tell me more",
                "That's a great point",
                "I was thinking the same thing",
                "Interesting perspective!"
            ],
            "question": [
                "What do you all think about {topic}?",
                "Anyone have experience with {topic}?",
                "I'm curious about {topic}, thoughts?",
                "Has anyone tried {topic} recently?"
            ]
        }
    
    async def decide_next_speaker(
        self, 
        warmer_session_id: int,
        group_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Decide who should speak next and what type of message
        
        Returns:
            Tuple of (session_name, message_type)
        """
        try:
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(
                    WarmerSession.id == warmer_session_id
                ).first()
                
                if not warmer:
                    raise ValueError(f"Warmer session {warmer_session_id} not found")
                
                all_sessions = warmer.all_sessions
                
                # Get recent conversation history
                recent_messages = self._get_recent_messages(db, warmer_session_id, group_id, limit=5)
                
                # If no recent messages, orchestrator starts
                if not recent_messages:
                    return warmer.orchestrator_session, "greeting"
                
                # Get last speaker
                last_speaker = recent_messages[0].sender_session if recent_messages else None
                
                # Choose next speaker (round-robin, excluding last speaker)
                available_speakers = [s for s in all_sessions if s != last_speaker]
                next_speaker = random.choice(available_speakers) if available_speakers else all_sessions[0]
                
                # Determine message type based on conversation flow
                message_type = "response"
                if len(recent_messages) % 3 == 0:  # Every 3rd message is a question
                    message_type = "question"
                
                return next_speaker, message_type
                
        except Exception as e:
            self.logger.error(f"Failed to decide next speaker: {str(e)}")
            # Fallback to orchestrator
            return warmer.orchestrator_session if warmer else "default", "response"
    
    async def generate_message(
        self,
        warmer_session_id: int,
        sender_session: str,
        message_type: str,
        group_id: Optional[str] = None,
        recipient_session: Optional[str] = None
    ) -> str:
        """Generate a message using LiteLLM or fallback templates"""
        try:
            # Get conversation context
            context = await self._build_conversation_context(
                warmer_session_id, 
                group_id, 
                recipient_session
            )
            
            # Try to use LiteLLM if available
            if self.litellm_available:
                try:
                    message = await self._generate_with_litellm(
                        sender_session,
                        message_type,
                        context
                    )
                    return message
                except Exception as e:
                    self.logger.warning(f"LiteLLM generation failed, using fallback: {str(e)}")
            
            # Fallback to templates
            return self._generate_fallback_message(message_type, context)
            
        except Exception as e:
            self.logger.error(f"Failed to generate message: {str(e)}")
            return "Hey! How's everyone doing?"
    
    async def _build_conversation_context(
        self,
        warmer_session_id: int,
        group_id: Optional[str] = None,
        recipient_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build conversation context for message generation"""
        try:
            with get_db() as db:
                # Get recent messages
                recent_messages = self._get_recent_messages(
                    db, 
                    warmer_session_id, 
                    group_id, 
                    limit=10
                )
                
                # Format conversation history
                conversation_history = []
                for msg in reversed(recent_messages):  # Chronological order
                    conversation_history.append({
                        "sender": msg.sender_session,
                        "message": msg.message_content,
                        "timestamp": msg.sent_at.isoformat() if msg.sent_at else None
                    })
                
                # Choose a topic if starting new conversation
                current_topic = None
                if not conversation_history:
                    current_topic = random.choice(self.conversation_topics)
                
                return {
                    "conversation_history": conversation_history,
                    "is_group": group_id is not None,
                    "recipient": recipient_session,
                    "current_topic": current_topic,
                    "message_count": len(conversation_history)
                }
                
        except Exception as e:
            self.logger.error(f"Failed to build context: {str(e)}")
            return {"conversation_history": [], "is_group": group_id is not None}
    
    async def _generate_with_litellm(
        self,
        sender: str,
        message_type: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate message using LiteLLM"""
        try:
            # Build conversation history for LLM
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt(message_type, context)
                }
            ]
            
            # Add conversation history
            for msg in context.get("conversation_history", [])[-5:]:  # Last 5 messages
                role = "assistant" if msg["sender"] == sender else "user"
                messages.append({
                    "role": role,
                    "content": msg["message"]
                })
            
            # Add generation instruction
            messages.append({
                "role": "user",
                "content": self._get_generation_prompt(message_type, context)
            })
            
            # Generate with LiteLLM based on provider
            if self.llm_provider == "groq":
                response = completion(
                    model=self.model,
                    messages=messages,
                    api_key=self.api_key,
                    temperature=0.8,
                    max_tokens=100
                )
            else:
                response = completion(
                    model=self.model,
                    messages=messages,
                    api_base=self.api_base,
                    temperature=0.8,
                    max_tokens=100
                )
            
            generated_message = response.choices[0].message.content.strip()
            
            # Clean up the message
            generated_message = generated_message.replace('"', '').strip()
            
            # Ensure message is appropriate length
            if len(generated_message) > 200:
                generated_message = generated_message[:200] + "..."
            
            return generated_message
            
        except Exception as e:
            self.logger.error(f"LiteLLM generation error: {str(e)}")
            raise
    
    def _get_system_prompt(self, message_type: str, context: Dict[str, Any]) -> str:
        """Get system prompt for LLM"""
        is_group = context.get("is_group", False)
        
        base_prompt = """You are participating in a casual WhatsApp conversation between friends. 
Keep messages natural, friendly, and conversational. Use casual language and occasional emojis.
Messages should be 1-2 sentences maximum. Be authentic and human-like."""
        
        if message_type == "greeting":
            return base_prompt + "\nStart a friendly conversation with a greeting."
        elif message_type == "question":
            topic = context.get("current_topic", "general topics")
            return base_prompt + f"\nAsk an engaging question about {topic} to keep the conversation going."
        else:  # response
            return base_prompt + "\nRespond naturally to the previous message."
    
    def _get_generation_prompt(self, message_type: str, context: Dict[str, Any]) -> str:
        """Get generation prompt for LLM"""
        if message_type == "greeting":
            return "Generate a friendly greeting message to start the conversation:"
        elif message_type == "question":
            topic = context.get("current_topic", random.choice(self.conversation_topics))
            return f"Generate a casual question about {topic}:"
        else:
            return "Generate a natural response to continue the conversation:"
    
    def _generate_fallback_message(self, message_type: str, context: Dict[str, Any]) -> str:
        """Generate message using fallback templates"""
        if message_type == "greeting":
            return random.choice(self.fallback_templates["greeting"])
        elif message_type == "question":
            template = random.choice(self.fallback_templates["question"])
            topic = context.get("current_topic", random.choice(self.conversation_topics))
            return template.format(topic=topic)
        else:
            return random.choice(self.fallback_templates["response"])
    
    def _get_recent_messages(
        self, 
        db: Session,
        warmer_session_id: int,
        group_id: Optional[str] = None,
        limit: int = 10
    ) -> List[WarmerConversation]:
        """Get recent messages from database"""
        query = db.query(WarmerConversation).filter(
            WarmerConversation.warmer_session_id == warmer_session_id
        )
        
        if group_id:
            query = query.filter(WarmerConversation.group_id == group_id)
        
        return query.order_by(WarmerConversation.sent_at.desc()).limit(limit).all()
    
    async def save_conversation(
        self,
        warmer_session_id: int,
        message_id: str,
        sender_session: str,
        message_content: str,
        message_type: MessageType,
        group_id: Optional[str] = None,
        recipient_session: Optional[str] = None
    ):
        """Save conversation to database"""
        try:
            with get_db() as db:
                conversation = WarmerConversation(
                    warmer_session_id=warmer_session_id,
                    message_id=message_id,
                    sender_session=sender_session,
                    recipient_session=recipient_session,
                    group_id=group_id,
                    message_type=message_type.value,
                    message_content=message_content
                )
                
                db.add(conversation)
                db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to save conversation: {str(e)}")
    
    def get_random_delay(self, is_group: bool, warmer_session_id: int) -> int:
        """Get random delay in seconds based on configuration"""
        try:
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(
                    WarmerSession.id == warmer_session_id
                ).first()
                
                if warmer:
                    if is_group:
                        return random.randint(
                            warmer.group_message_delay_min,
                            warmer.group_message_delay_max
                        )
                    else:
                        return random.randint(
                            warmer.direct_message_delay_min,
                            warmer.direct_message_delay_max
                        )
                
        except Exception as e:
            self.logger.error(f"Failed to get delay config: {str(e)}")
        
        # Default delays
        return random.randint(30, 300) if is_group else random.randint(120, 600)