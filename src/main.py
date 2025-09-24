"""
Main MCP Server Application
Orchestrates the entire Totara LMS chatbot flow using Haystack framework
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import json
from mcp.server import Server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    TextContent,
    Tool,
    ListToolsResult,
)

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
            # Initialize Haystack pipeline
            await self.haystack_pipeline.initialize()
            
            # Start session manager
            await self.session_manager.start()
            
            # Initialize knowledge base
            await self.knowledge_base.initialize_knowledge_base()
            
            self.is_initialized = True
            logger.info("Totara LMS Chatbot initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing chatbot: {e}")
            raise
    
    async def process_user_query(self, user_id: str, user_query: str,
                               user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main method to process user queries
        """
        if not self.is_initialized:
            await self.initialize()
        
        async def query_processor(session, user_message, **kwargs):
            # Get enhanced context from knowledge base
            contextual_info = await self.knowledge_base.get_contextual_information(
                user_message, session.get_recent_context()
            )
            
            # Create query context
            query_context = QueryContext(
                user_id=user_id,
                session_id=session.session_id,
                user_query=user_message,
                conversation_history=session.get_recent_context(),
                user_profile=session.user_context
            )
            
            # Add contextual information to user profile
            if contextual_info:
                query_context.user_profile = query_context.user_profile or {}
                query_context.user_profile['contextual_info'] = contextual_info
            
            # Process query through Haystack pipeline
            response = await self.haystack_pipeline.process_query(query_context)
            
            # Add conversation turn to session
            self.session_manager.add_conversation_turn(
                session.session_id,
                user_message,
                response.response_text,
                response.sql_query,
                response.confidence,
                {"requires_followup": response.requires_followup}
            )
            
            # Add successful interactions to knowledge base
            if response.confidence > 0.7:
                await self.knowledge_base.add_conversation_context(
                    session.session_id,
                    user_message,
                    response.response_text,
                    response.sql_query
                )
            
            return response
        
        # Process with thread safety
        try:
            response = await self.context_manager.process_user_request(
                user_id, user_query, query_processor, user_context=user_context
            )
            
            # Convert to dictionary for JSON serialization
            return {
                "response": response.response_text,
                "sql_query": response.sql_query,
                "confidence": response.confidence,
                "session_id": response.session_id,
                "requires_followup": response.requires_followup,
                "data": response.data
            }
            
        except Exception as e:
            logger.error(f"Error processing query for user {user_id}: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
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
            "system_status": "operational" if self.is_initialized else "initializing"
        }
    
    async def close_user_session(self, user_id: str) -> bool:
        """Close a user session"""
        session = self.session_manager.get_user_session(user_id)
        if session:
            return self.session_manager.close_session(session.session_id)
        return False
    
    async def cleanup(self):
        """Cleanup all resources"""
        logger.info("Cleaning up Totara LMS Chatbot...")
        
        await self.session_manager.stop()
        await self.haystack_pipeline.cleanup()
        self.knowledge_base.close()
        
        logger.info("Cleanup completed")


class TotaraLMSMCPServer:
    """
    MCP Server wrapper for the Totara LMS Chatbot
    """
    
    def __init__(self):
        self.config = Config()
        self.chatbot = TotaraLMSChatbot(self.config)
        self.mcp_server = McpServer("totara-lms-chatbot")
        self._setup_tools()
    
    def _setup_tools(self):
        """Setup MCP tools"""
        
        @self.mcp_server.get_tools()
        async def get_tools() -> GetToolsResult:
            return GetToolsResult(
                tools=[
                    Tool(
                        name="chat",
                        description="Chat with the Totara LMS assistant",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string", "description": "User identifier"},
                                "message": {"type": "string", "description": "User message"},
                                "user_context": {"type": "object", "description": "Optional user context"}
                            },
                            "required": ["user_id", "message"]
                        }
                    ),
                    Tool(
                        name="get_session_info",
                        description="Get user session information",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string", "description": "User identifier"}
                            },
                            "required": ["user_id"]
                        }
                    ),
                    Tool(
                        name="get_system_stats",
                        description="Get system statistics",
                        inputSchema={
                            "type": "object",
                            "properties": {}
                        }
                    ),
                    Tool(
                        name="close_session",
                        description="Close a user session",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string", "description": "User identifier"}
                            },
                            "required": ["user_id"]
                        }
                    )
                ]
            )
        
        @self.mcp_server.call_tool()
        async def call_tool(params: CallToolRequestParams) -> CallToolResult:
            try:
                args = params.arguments or {}
                
                if params.name == "chat":
                    user_id = args.get("user_id", "")
                    message = args.get("message", "")
                    user_context = args.get("user_context")
                    
                    if not user_id or not message:
                        return CallToolResult(
                            content=[TextContent(type="text", text="Error: user_id and message are required")]
                        )
                    
                    result = await self.chatbot.process_user_query(
                        user_id, message, user_context
                    )
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                elif params.name == "get_session_info":
                    user_id = args.get("user_id", "")
                    if not user_id:
                        return CallToolResult(
                            content=[TextContent(type="text", text="Error: user_id is required")]
                        )
                    
                    result = await self.chatbot.get_user_session_info(user_id)
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                elif params.name == "get_system_stats":
                    result = await self.chatbot.get_system_stats()
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                elif params.name == "close_session":
                    user_id = args.get("user_id", "")
                    if not user_id:
                        return CallToolResult(
                            content=[TextContent(type="text", text="Error: user_id is required")]
                        )
                    
                    result = await self.chatbot.close_user_session(user_id)
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps({"success": result}))]
                    )
                
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {params.name}")]
                    )
                    
            except Exception as e:
                logger.error(f"Error in tool call {params.name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
    
    async def run(self):
        """Run the MCP server"""
        try:
            logger.info("Starting Totara LMS MCP Server...")
            await self.chatbot.initialize()
            
            # Run the MCP server
            await self.mcp_server.run()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await self.chatbot.cleanup()


async def main():
    """Main entry point"""
    server = TotaraLMSMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())