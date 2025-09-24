"""
Configuration management for Totara LMS Chatbot
"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration class for the Totara LMS Chatbot"""
    
    # Database configuration
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_name: str = os.getenv("DB_NAME", "totara_lms")
    db_username: str = os.getenv("DB_USERNAME", "root")
    db_password: str = os.getenv("DB_PASSWORD", "")
    
    # LLM configuration
    llm_model: str = os.getenv("LLM_MODEL", "llama3.1:8b")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    
    # Session management
    session_timeout_minutes: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))
    cleanup_interval_minutes: int = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "10"))
    
    # ChromaDB configuration
    chromadb_collection: str = os.getenv("CHROMADB_COLLECTION", "totara_knowledge")
    chromadb_persist_dir: str = os.getenv("CHROMADB_PERSIST_DIR", "./chromadb_data")
    
    # MCP Server configuration
    mcp_server_name: str = os.getenv("MCP_SERVER_NAME", "totara-lms-chatbot")
    mcp_server_version: str = os.getenv("MCP_SERVER_VERSION", "1.0.0")
    
    # Logging configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[str] = os.getenv("LOG_FILE")
    
    # Security configuration
    max_query_length: int = int(os.getenv("MAX_QUERY_LENGTH", "1000"))
    max_conversation_history: int = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))
    
    def validate(self) -> bool:
        """Validate configuration"""
        required_fields = [
            self.db_host,
            self.db_name,
            self.db_username,
            self.llm_model
        ]
        
        for field in required_fields:
            if not field:
                return False
        
        return True
    
    def __post_init__(self):
        """Post-initialization validation"""
        if not self.validate():
            raise ValueError("Invalid configuration: missing required fields")