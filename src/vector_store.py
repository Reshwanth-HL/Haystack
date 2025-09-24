"""
ChromaDB Vector Store for Enhanced Context and Knowledge Retrieval
Provides semantic search capabilities for Totara LMS documentation and context
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Document chunk for vector storage"""
    id: str
    content: str
    metadata: Dict[str, Any]
    source: str
    chunk_index: int = 0


@dataclass
class SearchResult:
    """Search result from vector store"""
    content: str
    metadata: Dict[str, Any]
    distance: float
    relevance_score: float


class TotaraKnowledgeBase:
    """
    ChromaDB-based knowledge base for Totara LMS context and documentation
    Provides semantic search for enhanced chatbot responses
    """
    
    def __init__(self, collection_name: str = "totara_knowledge", 
                 persist_directory: str = "./chromadb_data"):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client: Optional[Any] = None
        self.collection: Optional[Any] = None
        self._initialize_client()
        
        # Predefined Totara LMS knowledge for bootstrapping
        self.totara_knowledge = [
            {
                "content": "Totara LMS is a learning management system designed for corporate training and development. It includes features for courses, certifications, learning plans, and performance management.",
                "metadata": {"type": "general", "category": "overview"},
                "source": "totara_docs"
            },
            {
                "content": "Users in Totara LMS have profiles containing personal information, enrollment history, completion records, and competency tracking.",
                "metadata": {"type": "user_management", "category": "profiles"},
                "source": "totara_docs"
            },
            {
                "content": "Courses in Totara can be enrolled through various methods: self-enrollment, manager assignment, automatic enrollment based on position or audience.",
                "metadata": {"type": "course_management", "category": "enrollment"},
                "source": "totara_docs"
            },
            {
                "content": "Learning plans in Totara help organize learning pathways and track progress towards specific competencies or goals.",
                "metadata": {"type": "learning_plans", "category": "pathways"},
                "source": "totara_docs"
            },
            {
                "content": "Certifications in Totara require periodic renewal and can have prerequisites, required courses, and recertification periods.",
                "metadata": {"type": "certifications", "category": "compliance"},
                "source": "totara_docs"
            },
            {
                "content": "Reporting in Totara provides insights into user progress, course completions, time spent learning, and organizational learning metrics.",
                "metadata": {"type": "reporting", "category": "analytics"},
                "source": "totara_docs"
            },
            {
                "content": "Face-to-face sessions in Totara allow scheduling of instructor-led training with attendance tracking and session management.",
                "metadata": {"type": "face_to_face", "category": "sessions"},
                "source": "totara_docs"
            },
            {
                "content": "Competencies in Totara define skills and knowledge areas that can be assessed, tracked, and linked to learning activities.",
                "metadata": {"type": "competencies", "category": "skills"},
                "source": "totara_docs"
            }
        ]
    
    def _initialize_client(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Totara LMS knowledge base for chatbot context"}
            )
            
            logger.info(f"ChromaDB initialized with collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise
    
    async def initialize_knowledge_base(self, force_reinit: bool = False):
        """Initialize the knowledge base with Totara LMS documentation"""
        try:
            # Check if knowledge base is already populated
            if not force_reinit and self.collection and self.collection.count() > 0:
                logger.info("Knowledge base already initialized")
                return
            
            logger.info("Initializing Totara knowledge base...")
            
            # Clear existing data if force reinit
            if force_reinit and self.client:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Totara LMS knowledge base for chatbot context"}
                )
            
            # Add predefined knowledge
            await self._add_knowledge_chunks(self.totara_knowledge)
            
            logger.info(f"Knowledge base initialized with {len(self.totara_knowledge)} documents")
            
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}")
            raise
    
    async def _add_knowledge_chunks(self, knowledge_items: List[Dict[str, Any]]):
        """Add knowledge chunks to the vector store"""
        if not self.collection:
            raise RuntimeError("Collection not initialized")
            
        documents = []
        metadatas = []
        ids = []
        
        for i, item in enumerate(knowledge_items):
            # Generate unique ID
            content_hash = hashlib.md5(item["content"].encode()).hexdigest()
            doc_id = f"{item['source']}_{content_hash}_{i}"
            
            documents.append(item["content"])
            metadatas.append({
                **item["metadata"],
                "source": item["source"],
                "added_at": datetime.now().isoformat(),
                "chunk_index": i
            })
            ids.append(doc_id)
        
        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    async def add_document(self, content: str, metadata: Dict[str, Any], 
                          source: str = "user_added") -> str:
        """Add a single document to the knowledge base"""
        try:
            if not self.collection:
                raise RuntimeError("Collection not initialized")
                
            # Generate unique ID
            content_hash = hashlib.md5(content.encode()).hexdigest()
            doc_id = f"{source}_{content_hash}_{datetime.now().timestamp()}"
            
            # Add metadata
            full_metadata = {
                **metadata,
                "source": source,
                "added_at": datetime.now().isoformat()
            }
            
            self.collection.add(
                documents=[content],
                metadatas=[full_metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Added document to knowledge base: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            raise
    
    async def search_knowledge(self, query: str, max_results: int = 5,
                             metadata_filter: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search the knowledge base for relevant information"""
        try:
            if not self.collection:
                logger.error("Collection not initialized")
                return []
                
            # Perform semantic search
            results = self.collection.query(
                query_texts=[query],
                n_results=max_results,
                where=metadata_filter
            )
            
            # Process results
            search_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Calculate relevance score (inverse of distance, normalized)
                    relevance_score = max(0, 1 - distance)
                    
                    search_results.append(SearchResult(
                        content=doc,
                        metadata=metadata,
                        distance=distance,
                        relevance_score=relevance_score
                    ))
            
            logger.debug(f"Found {len(search_results)} relevant documents for query: {query}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    async def get_contextual_information(self, user_query: str, 
                                       conversation_history: List[Dict[str, str]],
                                       max_context_length: int = 1000) -> str:
        """Get contextual information to enhance chatbot responses"""
        try:
            # Search for relevant knowledge
            search_results = await self.search_knowledge(user_query, max_results=3)
            
            if not search_results:
                return ""
            
            # Build context string
            context_parts = []
            current_length = 0
            
            context_parts.append("Relevant Totara LMS context:")
            
            for result in search_results:
                if result.relevance_score > 0.3:  # Only include relevant results
                    context_text = f"- {result.content}"
                    if current_length + len(context_text) <= max_context_length:
                        context_parts.append(context_text)
                        current_length += len(context_text)
                    else:
                        break
            
            return "\n".join(context_parts) if len(context_parts) > 1 else ""
            
        except Exception as e:
            logger.error(f"Error getting contextual information: {e}")
            return ""
    
    async def add_conversation_context(self, session_id: str, user_query: str,
                                     bot_response: str, sql_query: Optional[str] = None):
        """Add successful conversation context to knowledge base for future reference"""
        try:
            # Create a knowledge entry from successful interactions
            if sql_query:
                content = f"User asked: '{user_query}'. SQL query used: {sql_query}. Response: {bot_response[:200]}..."
                metadata = {
                    "type": "conversation",
                    "category": "sql_example",
                    "session_id": session_id,
                    "has_sql": True
                }
            else:
                content = f"User asked: '{user_query}'. Response: {bot_response[:200]}..."
                metadata = {
                    "type": "conversation",
                    "category": "general_qa",
                    "session_id": session_id,
                    "has_sql": False
                }
            
            await self.add_document(content, metadata, "conversation_history")
            
        except Exception as e:
            logger.error(f"Error adding conversation context: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        try:
            if not self.collection:
                return {"error": "Collection not initialized"}
                
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
    
    async def update_document(self, doc_id: str, content: str, 
                            metadata: Dict[str, Any]) -> bool:
        """Update an existing document in the knowledge base"""
        try:
            if not self.collection:
                logger.error("Collection not initialized")
                return False
                
            # ChromaDB doesn't have direct update, so we delete and re-add
            self.collection.delete(ids=[doc_id])
            
            # Add updated document
            full_metadata = {
                **metadata,
                "updated_at": datetime.now().isoformat()
            }
            
            self.collection.add(
                documents=[content],
                metadatas=[full_metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Updated document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {e}")
            return False
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the knowledge base"""
        try:
            if not self.collection:
                logger.error("Collection not initialized")
                return False
                
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    def close(self):
        """Close the ChromaDB client"""
        # ChromaDB client doesn't need explicit closing
        logger.info("ChromaDB client closed")