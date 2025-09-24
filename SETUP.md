# Quick Setup Guide

## Prerequisites

1. **Python 3.8+** installed
2. **MySQL Server** with Totara LMS database
3. **Ollama** installed and running with llama3.1:8b model
4. **Git** (optional, for version control)

## Installation Steps

### 1. Clone and Setup Project
```bash
# Navigate to project directory
cd "c:\Users\Reshwanth-HL\Haystack"

# Install dependencies
pip install -r requirements.txt

# Alternative: Install in development mode
pip install -e .
```

### 2. Configure Environment
```bash
# Copy environment template
copy .env.example .env

# Edit .env file with your actual values:
# - Database credentials
# - Ollama URL (if different)
# - Other settings as needed
```

### 3. Setup Ollama
```bash
# Install llama3.1:8b model (if not already installed)
ollama pull llama3.1:8b

# Verify model is available
ollama list
```

### 4. Database Setup
- Ensure MySQL server is running
- Create Totara LMS database (if not exists)
- Update database credentials in .env file
- Test database connection

### 5. Run the Server
```bash
# Method 1: Using startup script
python run_server.py

# Method 2: Direct execution
python -m src.main

# Method 3: Development mode
python src/main.py
```

## Testing the Setup

### 1. Check System Status
```bash
# Using MCP client or direct API call
curl -X POST http://localhost:8000/tools/get_system_stats
```

### 2. Test Chat Functionality
```bash
# Example chat request
{
    "tool": "chat",
    "arguments": {
        "user_id": "test_user_123",
        "message": "Show me my enrolled courses"
    }
}
```

## Configuration Options

### Database Settings (.env)
```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=totara_lms
DB_USERNAME=your_username
DB_PASSWORD=your_password
```

### LLM Settings (.env)
```
LLM_MODEL=llama3.1:8b
OLLAMA_URL=http://localhost:11434
```

### Session Management (.env)
```
SESSION_TIMEOUT_MINUTES=60
CLEANUP_INTERVAL_MINUTES=10
```

## Architecture Overview

```
User Query → MCP Server → Haystack Pipeline → LLM Brain → SQL Generation → MySQL
                ↓
            Session Management & Thread Handling
                ↓
            ChromaDB Vector Storage
```

## Key Components

1. **MCP Server**: Handles client connections and tool routing
2. **Haystack Pipeline**: Orchestrates LLM-powered query processing
3. **Database Connector**: Manages MySQL connections and SQL execution
4. **Session Manager**: Handles multi-user conversations and state
5. **Vector Store**: ChromaDB for enhanced context and knowledge retrieval
6. **LLM Brain**: llama3.1:8b controlling the entire conversation flow

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check MySQL server is running
   - Verify credentials in .env file
   - Test network connectivity

2. **Ollama Model Not Found**
   ```bash
   ollama pull llama3.1:8b
   ```

3. **ChromaDB Initialization Error**
   - Check write permissions in project directory
   - Ensure sufficient disk space

4. **Session Timeout Issues**
   - Adjust SESSION_TIMEOUT_MINUTES in .env
   - Check system clock synchronization

### Logs and Debugging

- Check console output for error messages
- Enable debug logging: `LOG_LEVEL=DEBUG` in .env
- Monitor database query logs
- Check Ollama server logs

## Production Deployment

For production use:

1. **Security**
   - Use strong database passwords
   - Implement proper authentication
   - Enable HTTPS/TLS

2. **Performance**
   - Optimize database queries
   - Configure connection pooling
   - Monitor resource usage

3. **Monitoring**
   - Set up logging to files
   - Implement health checks
   - Monitor session statistics

## Support

For issues or questions:
1. Check logs for error messages
2. Verify all prerequisites are met
3. Test individual components separately
4. Review configuration settings