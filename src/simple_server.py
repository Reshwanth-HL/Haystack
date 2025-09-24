"""
Simplified MCP Server Application using FastMCP
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import json
from mcp.server.fastmcp import FastMCP

# Import our custom modules
from .database_connector import DatabaseConfig
from .haystack_pipeline import HaystackPipeline, QueryContext
from .session_manager import SessionManager, ThreadSafeContextManager
from .vector_store import TotaraKnowledgeBase
from .config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TotaraLMSChatbot:
    """
    Main chatbot class that integrates all components
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize components
        self.db_config = DatabaseConfig(
            host=config.db_host,
            port=config.db_port,
            database=config.db_name,
            username=config.db_username,
            password=config.db_password
        )
        
        self.haystack_pipeline = HaystackPipeline(
            db_config=self.db_config,
            model_name=config.llm_model
        )
        
        self.session_manager = SessionManager(
            session_timeout_minutes=config.session_timeout_minutes,
            cleanup_interval_minutes=config.cleanup_interval_minutes
        )
        
        self.context_manager = ThreadSafeContextManager(self.session_manager)
        
        self.knowledge_base = TotaraKnowledgeBase(
            collection_name=config.chromadb_collection,
            persist_directory=config.chromadb_persist_dir
        )
        
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize all components"""
        if self.is_initialized:
            return
            
        logger.info("Initializing Totara LMS Chatbot...")
        
        try:
            # Initialize Haystack pipeline (skip DB connection for now)
            logger.info("Skipping database connection - initialize pipeline without DB")
            
            # Start session manager
            await self.session_manager.start()
            
            # Initialize knowledge base
            await self.knowledge_base.initialize_knowledge_base()
            
            self.is_initialized = True
            logger.info("Totara LMS Chatbot initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing chatbot: {e}")
            # Don't raise - continue with limited functionality
    
    async def process_user_query(self, user_id: str, user_query: str,
                               user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main method to process user queries
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # For demo purposes, return a simulated response
            logger.info(f"Processing query from user {user_id}: {user_query}")
            
            # Get enhanced context from knowledge base
            contextual_info = await self.knowledge_base.get_contextual_information(
                user_query, []
            )
            
            # Simulate processing
            response = {
                "response": f"Thank you for your query: '{user_query}'. This is a simulated response from the Totara LMS chatbot. The system architecture is working! Context found: {bool(contextual_info)}",
                "sql_query": "SELECT * FROM users WHERE username = 'demo'  -- Simulated query",
                "confidence": 0.8,
                "session_id": f"session_{user_id}",
                "requires_followup": False,
                "data": [{"demo": "data", "user_query": user_query}],
                "status": "demo_mode"
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query for user {user_id}: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your request. The system is in demo mode.",
                "sql_query": None,
                "confidence": 0.1,
                "session_id": None,
                "requires_followup": False,
                "data": None,
                "error": str(e)
            }
    
    async def get_user_session_info(self, user_id: str) -> Dict[str, Any]:
        """Get user session information"""
        session = self.session_manager.get_user_session(user_id)
        if session:
            return {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "conversation_turns": len(session.conversation_history),
                "is_active": session.is_active
            }
        return {"error": "No active session found"}
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        session_stats = self.session_manager.get_session_stats()
        kb_stats = self.knowledge_base.get_collection_stats()
        
        return {
            "session_stats": session_stats,
            "knowledge_base_stats": kb_stats,
            "system_status": "demo_mode" if self.is_initialized else "initializing",
            "note": "Database connection pending - running in demo mode"
        }
    
    async def cleanup(self):
        """Cleanup all resources"""
        logger.info("Cleaning up Totara LMS Chatbot...")
        
        await self.session_manager.stop()
        if hasattr(self.haystack_pipeline, 'cleanup'):
            await self.haystack_pipeline.cleanup()
        self.knowledge_base.close()
        
        logger.info("Cleanup completed")


# Initialize FastMCP server
mcp = FastMCP("Totara LMS Chatbot")
chatbot = None


@mcp.tool()
async def chat(user_id: str, message: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Chat with the Totara LMS assistant"""
    global chatbot
    if not chatbot:
        config = Config()
        chatbot = TotaraLMSChatbot(config)
        await chatbot.initialize()
    
    return await chatbot.process_user_query(user_id, message, user_context)


@mcp.tool()
async def get_session_info(user_id: str) -> Dict[str, Any]:
    """Get user session information"""
    global chatbot
    if not chatbot:
        return {"error": "Chatbot not initialized"}
    
    return await chatbot.get_user_session_info(user_id)


@mcp.tool()
async def get_system_stats() -> Dict[str, Any]:
    """Get system statistics"""
    global chatbot
    if not chatbot:
        config = Config()
        chatbot = TotaraLMSChatbot(config)
        await chatbot.initialize()
    
    return await chatbot.get_system_stats()


@mcp.tool()
async def close_session(user_id: str) -> Dict[str, bool]:
    """Close a user session"""
    global chatbot
    if not chatbot:
        return {"success": False}
    
    result = await chatbot.close_user_session(user_id)
    return {"success": result}


async def main():
    """Main entry point"""
    try:
        logger.info("Starting Totara LMS MCP Server with FastMCP...")
        
        # Initialize global chatbot
        global chatbot
        config = Config()
        chatbot = TotaraLMSChatbot(config)
        await chatbot.initialize()
        
        logger.info("Server ready! Use MCP client to connect and test.")
        logger.info("Available tools: chat, get_session_info, get_system_stats, close_session")
        
        # Run the server (this depends on how FastMCP is configured)
        await mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        if chatbot:
            await chatbot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())