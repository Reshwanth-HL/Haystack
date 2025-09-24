"""
MySQL Database Connector for Totara LMS
Handles SQL query generation and execution with LLM guidance
"""

import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    database: str
    username: str
    password: str
    charset: str = "utf8mb4"


@dataclass
class QueryResult:
    """Query execution result"""
    success: bool
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    error: Optional[str] = None


class TotaraLMSConnector:
    """
    MySQL connector specifically designed for Totara LMS database
    Includes LLM-guided SQL query generation and execution
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection: Optional[mysql.connector.MySQLConnection] = None
        self.cursor: Optional[Any] = None
        
        # Common Totara LMS table schema information for LLM context
        self.totara_schema = {
            "users": ["id", "username", "firstname", "lastname", "email", "timecreated", "timemodified"],
            "courses": ["id", "fullname", "shortname", "summary", "category", "timecreated", "timemodified"],
            "course_enrollments": ["id", "userid", "courseid", "timeenrolled", "status"],
            "course_completions": ["id", "userid", "course", "timecompleted", "grade"],
            "learning_plans": ["id", "userid", "name", "description", "status", "timecreated"],
            "certifications": ["id", "userid", "certifid", "status", "timecompleted"],
            "programs": ["id", "fullname", "shortname", "summary", "visible"],
            "grades": ["id", "userid", "itemid", "finalgrade", "timecreated", "timemodified"],
            "quiz_attempts": ["id", "quiz", "userid", "attempt", "timestart", "timefinish", "sumgrades"],
            "sessions": ["id", "userid", "facetoface", "sessiondate", "status"],
            "feedback": ["id", "course", "userid", "completed", "timemodified"]
        }

    async def connect(self) -> bool:
        """Establish database connection"""
        try:
            # Azure MySQL specific connection parameters
            connection_config = {
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database,
                'user': self.config.username,
                'password': self.config.password,
                'charset': self.config.charset,
                'autocommit': True,
                'ssl_disabled': False,  # Enable SSL for Azure MySQL
                'use_unicode': True,
                'connection_timeout': 30,
                'auth_plugin': 'mysql_native_password'
            }
            
            self.connection = mysql.connector.connect(**connection_config)
            if self.connection:
                self.cursor = self.connection.cursor(dictionary=True)
            logger.info("Successfully connected to Totara LMS database")
            return True
        except Error as e:
            logger.error(f"Error connecting to database: {e}")
            return False

    async def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Database connection closed")

    def get_schema_context(self) -> str:
        """Get schema context for LLM to understand database structure"""
        schema_info = "Totara LMS Database Schema:\n"
        for table, columns in self.totara_schema.items():
            schema_info += f"Table: {table}\n"
            schema_info += f"Columns: {', '.join(columns)}\n\n"
        return schema_info

    async def execute_query(self, sql_query: str, params: Optional[tuple] = None) -> QueryResult:
        """
        Execute SQL query safely with proper error handling
        """
        try:
            if not self.connection or not self.connection.is_connected():
                await self.connect()
            
            if not self.cursor:
                raise Error("Database cursor not available")
            
            # Execute query
            self.cursor.execute(sql_query, params or ())
            
            # Fetch results for SELECT queries
            if sql_query.strip().upper().startswith('SELECT'):
                data = self.cursor.fetchall()
                columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
                row_count = len(data)
                
                return QueryResult(
                    success=True,
                    data=data,
                    columns=columns,
                    row_count=row_count
                )
            else:
                # For non-SELECT queries
                return QueryResult(
                    success=True,
                    data=[],
                    columns=[],
                    row_count=self.cursor.rowcount if self.cursor else 0
                )
                
        except Error as e:
            logger.error(f"Error executing query: {e}")
            return QueryResult(
                success=False,
                data=[],
                columns=[],
                row_count=0,
                error=str(e)
            )

    def validate_sql_query(self, query: str) -> bool:
        """
        Basic SQL query validation for security
        Prevents dangerous operations like DROP, DELETE without WHERE, etc.
        """
        query_upper = query.upper().strip()
        
        # Block dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        
        for keyword in dangerous_keywords:
            if query_upper.startswith(keyword):
                logger.warning(f"Blocked potentially dangerous query starting with {keyword}")
                return False
        
        # Ensure it's a SELECT query
        if not query_upper.startswith('SELECT'):
            logger.warning("Only SELECT queries are allowed")
            return False
            
        return True

    async def get_user_data(self, user_identifier: str, identifier_type: str = "username") -> QueryResult:
        """Get user data by username or email"""
        if identifier_type == "username":
            query = "SELECT * FROM users WHERE username = %s"
        elif identifier_type == "email":
            query = "SELECT * FROM users WHERE email = %s"
        else:
            return QueryResult(
                success=False,
                data=[],
                columns=[],
                row_count=0,
                error="Invalid identifier type"
            )
        
        return await self.execute_query(query, (user_identifier,))

    async def get_user_courses(self, user_id: int) -> QueryResult:
        """Get courses enrolled by a user"""
        query = """
        SELECT c.id, c.fullname, c.shortname, ce.timeenrolled, ce.status
        FROM courses c
        JOIN course_enrollments ce ON c.id = ce.courseid
        WHERE ce.userid = %s
        ORDER BY ce.timeenrolled DESC
        """
        return await self.execute_query(query, (user_id,))

    async def get_user_completions(self, user_id: int) -> QueryResult:
        """Get course completions for a user"""
        query = """
        SELECT c.fullname, cc.timecompleted, cc.grade
        FROM course_completions cc
        JOIN courses c ON cc.course = c.id
        WHERE cc.userid = %s
        ORDER BY cc.timecompleted DESC
        """
        return await self.execute_query(query, (user_id,))

    async def get_course_statistics(self) -> QueryResult:
        """Get general course statistics"""
        query = """
        SELECT 
            COUNT(*) as total_courses,
            COUNT(CASE WHEN visible = 1 THEN 1 END) as visible_courses,
            AVG(CASE WHEN timecreated > 0 THEN timecreated END) as avg_creation_time
        FROM courses
        """
        return await self.execute_query(query)

    async def search_courses(self, search_term: str) -> QueryResult:
        """Search courses by name or description"""
        query = """
        SELECT id, fullname, shortname, summary
        FROM courses
        WHERE fullname LIKE %s OR summary LIKE %s OR shortname LIKE %s
        LIMIT 20
        """
        search_pattern = f"%{search_term}%"
        return await self.execute_query(query, (search_pattern, search_pattern, search_pattern))