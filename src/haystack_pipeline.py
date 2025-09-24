"""
Haystack Pipeline with LLM Brain Integration
Orchestrates the entire flow from natural language query to SQL generation and response creation
"""

from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
from haystack import Pipeline
from haystack.components.generators import OllamaGenerator
from haystack.components.builders import PromptBuilder
import json

from .database_connector import TotaraLMSConnector, QueryResult, DatabaseConfig

logger = logging.getLogger(__name__)


@dataclass
class QueryContext:
    """Context for query processing"""
    user_id: str
    session_id: str
    user_query: str
    conversation_history: List[Dict[str, str]]
    user_profile: Optional[Dict[str, Any]] = None


@dataclass
class ProcessedResponse:
    """Processed response from the pipeline"""
    response_text: str
    sql_query: Optional[str]
    data: Optional[List[Dict[str, Any]]]
    confidence: float
    session_id: str
    requires_followup: bool = False


class LLMBrain:
    """
    Central LLM Brain that controls the entire conversation flow
    Acts as the orchestrator for all operations
    """
    
    def __init__(self, model_name: str = "llama3.1:8b"):
        self.model_name = model_name
        self.llm = OllamaGenerator(
            model=model_name,
            url="http://localhost:11434/api/generate",
            generation_kwargs={
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 1000
            }
        )
        
        # System prompts for different tasks
        self.system_prompts = {
            "intent_analysis": """You are an AI assistant specialized in understanding user intents for a Totara LMS (Learning Management System) database. 
Analyze the user's query and determine:
1. What information they're seeking
2. What database tables might be involved
3. Whether this requires SQL query generation
4. The complexity level (simple lookup, complex analysis, etc.)

Respond with JSON format:
{
    "intent": "description of what user wants",
    "requires_sql": true/false,
    "tables_involved": ["table1", "table2"],
    "complexity": "simple|medium|complex",
    "query_type": "user_info|course_info|enrollment|completion|general_stats|other"
}""",

            "sql_generation": """You are an expert SQL query generator for Totara LMS database. 
Generate ONLY safe SELECT queries based on the user's intent and schema provided.

RULES:
- Only SELECT statements allowed
- Use proper JOINs for related data
- Include appropriate WHERE clauses
- Add ORDER BY and LIMIT for performance
- Use parameterized queries when possible

Database Schema:
{schema_info}

User Intent: {intent}
User Query: {user_query}

Generate a single, safe SQL query:""",

            "response_generation": """You are a friendly, knowledgeable university chatbot assistant. 
Create a conversational response based on the query results and context.

Context:
- User Query: {user_query}
- SQL Query Used: {sql_query}
- Data Retrieved: {query_data}
- User Profile: {user_profile}

Create a natural, helpful response that:
1. Directly answers the user's question
2. Explains the data in an easy-to-understand way
3. Offers relevant follow-up suggestions
4. Maintains a friendly, professional tone

Response:"""
        }

    async def analyze_intent(self, query_context: QueryContext) -> Dict[str, Any]:
        """Analyze user intent and determine processing strategy"""
        prompt = f"{self.system_prompts['intent_analysis']}\n\nUser Query: {query_context.user_query}"
        
        try:
            result = self.llm.run(prompt=prompt)
            response_text = result["replies"][0] if result["replies"] else "{}"
            
            # Parse JSON response
            intent_data = json.loads(response_text)
            return intent_data
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing intent analysis: {e}")
            return {
                "intent": "general inquiry",
                "requires_sql": False,
                "tables_involved": [],
                "complexity": "simple",
                "query_type": "other"
            }

    async def generate_sql_query(self, query_context: QueryContext, 
                                intent_data: Dict[str, Any], 
                                schema_info: str) -> Optional[str]:
        """Generate SQL query based on intent and schema"""
        if not intent_data.get("requires_sql", False):
            return None
            
        prompt = self.system_prompts["sql_generation"].format(
            schema_info=schema_info,
            intent=intent_data["intent"],
            user_query=query_context.user_query
        )
        
        try:
            result = self.llm.run(prompt=prompt)
            sql_query = result["replies"][0] if result["replies"] else ""
            
            # Clean up the response to extract just the SQL
            sql_query = sql_query.strip()
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            
            return sql_query.strip()
        except Exception as e:
            logger.error(f"Error generating SQL query: {e}")
            return None

    async def generate_response(self, query_context: QueryContext,
                               sql_query: Optional[str],
                               query_result: Optional[QueryResult]) -> str:
        """Generate final conversational response"""
        query_data = "No data retrieved" if not query_result or not query_result.success else str(query_result.data)
        
        prompt = self.system_prompts["response_generation"].format(
            user_query=query_context.user_query,
            sql_query=sql_query or "No SQL query used",
            query_data=query_data,
            user_profile=query_context.user_profile or "No profile available"
        )
        
        try:
            result = self.llm.run(prompt=prompt)
            return result["replies"][0] if result["replies"] else "I apologize, but I couldn't generate a proper response."
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I encountered an error while processing your request."


class HaystackPipeline:
    """
    Main Haystack pipeline that orchestrates the entire flow
    """
    
    def __init__(self, db_config: DatabaseConfig, model_name: str = "llama3.1:8b"):
        self.db_connector = TotaraLMSConnector(db_config)
        self.llm_brain = LLMBrain(model_name)
        self.pipeline = None
        self._build_pipeline()

    def _build_pipeline(self):
        """Build the Haystack pipeline components"""
        # Create pipeline components
        intent_analyzer = PromptBuilder(
            template=self.llm_brain.system_prompts["intent_analysis"] + "\n\nUser Query: {query}"
        )
        
        sql_generator = PromptBuilder(
            template=self.llm_brain.system_prompts["sql_generation"]
        )
        
        response_generator = PromptBuilder(
            template=self.llm_brain.system_prompts["response_generation"]
        )
        
        # Build the pipeline
        self.pipeline = Pipeline()
        self.pipeline.add_component("intent_analyzer", intent_analyzer)
        self.pipeline.add_component("sql_generator", sql_generator)
        self.pipeline.add_component("response_generator", response_generator)
        self.pipeline.add_component("llm", self.llm_brain.llm)

    async def initialize(self):
        """Initialize pipeline and database connection"""
        await self.db_connector.connect()
        logger.info("Haystack pipeline initialized successfully")

    async def process_query(self, query_context: QueryContext) -> ProcessedResponse:
        """
        Main processing method that handles the entire flow
        """
        try:
            # Step 1: Analyze user intent
            logger.info(f"Analyzing intent for query: {query_context.user_query}")
            intent_data = await self.llm_brain.analyze_intent(query_context)
            
            # Step 2: Generate SQL query if needed
            sql_query = None
            query_result = None
            
            if intent_data.get("requires_sql", False):
                logger.info("Generating SQL query")
                schema_info = self.db_connector.get_schema_context()
                sql_query = await self.llm_brain.generate_sql_query(
                    query_context, intent_data, schema_info
                )
                
                # Step 3: Execute SQL query
                if sql_query and self.db_connector.validate_sql_query(sql_query):
                    logger.info(f"Executing SQL query: {sql_query}")
                    query_result = await self.db_connector.execute_query(sql_query)
                else:
                    logger.warning("Invalid or dangerous SQL query blocked")
                    query_result = QueryResult(
                        success=False,
                        data=[],
                        columns=[],
                        row_count=0,
                        error="Invalid or unsafe query"
                    )
            
            # Step 4: Generate conversational response
            logger.info("Generating final response")
            response_text = await self.llm_brain.generate_response(
                query_context, sql_query, query_result
            )
            
            # Calculate confidence based on success of operations
            confidence = 0.9 if (not intent_data.get("requires_sql") or 
                               (query_result and query_result.success)) else 0.6
            
            return ProcessedResponse(
                response_text=response_text,
                sql_query=sql_query,
                data=query_result.data if query_result else None,
                confidence=confidence,
                session_id=query_context.session_id,
                requires_followup=intent_data.get("complexity") == "complex"
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return ProcessedResponse(
                response_text="I apologize, but I encountered an error while processing your request. Please try again.",
                sql_query=None,
                data=None,
                confidence=0.1,
                session_id=query_context.session_id,
                requires_followup=False
            )

    async def cleanup(self):
        """Cleanup resources"""
        await self.db_connector.disconnect()
        logger.info("Pipeline cleanup completed")