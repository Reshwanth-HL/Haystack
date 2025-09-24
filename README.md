# 🎓 Totara LMS Chatbot - Haystack MCP Server

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Haystack](https://img.shields.io/badge/Haystack-2.0+-green.svg)](https://haystack.deepset.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A sophisticated **university-ready chatbot system** built with Haystack framework and Model Context Protocol (MCP) for Totara LMS data interaction. Features **llama3.1:8b as the central brain** controlling the entire conversational flow.

## 🏗️ Architecture Overview

```
User Query → MCP Server → Haystack Pipeline → LLM Brain → SQL Generation → MySQL → Response
                ↓
            Session Management & Thread Handling
                ↓
            ChromaDB Vector Storage for Enhanced Context
```

### 🧠 **LLM-Controlled Flow**
The **llama3.1:8b model acts as the central brain** that:
- **Analyzes user intent** and determines processing strategy
- **Generates safe SQL queries** for Totara LMS database
- **Crafts conversational responses** based on retrieved data
- **Maintains context** across conversation threads

## 🚀 Key Features

- ✅ **Natural Language to SQL**: Intelligent query generation from user questions
- ✅ **Multi-User Sessions**: Thread-safe conversation handling for concurrent users
- ✅ **Context-Aware Responses**: ChromaDB vector storage for enhanced understanding
- ✅ **Totara LMS Integration**: Pre-configured for university learning management systems
- ✅ **Security First**: Query validation and sanitization
- ✅ **MCP Protocol**: Standard interface for tool integration
- ✅ **Production Ready**: Comprehensive error handling and logging

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM Brain** | llama3.1:8b (Ollama) | Central intelligence & conversation control |
| **Framework** | Haystack AI | Pipeline orchestration & LLM integration |
| **Database** | MySQL | Totara LMS data storage |
| **Vector Store** | ChromaDB | Semantic search & context enhancement |
| **Protocol** | MCP (Model Context Protocol) | Standardized tool interface |
| **Session Mgmt** | Custom Thread-Safe Manager | Multi-user conversation handling |

## 📋 Prerequisites

- **Python 3.8+**
- **MySQL Server** with Totara LMS database
- **Ollama** with llama3.1:8b model
- **Git** (for cloning)

## ⚡ Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Reshwanth-HL/Haystack.git
cd Haystack
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 4. Setup Ollama
```bash
# Install llama3.1:8b model
ollama pull llama3.1:8b

# Verify installation
ollama list
```

### 5. Run Demo
```bash
# Test the architecture
python test_demo.py
```

### 6. Start Server
```bash
# Run the MCP server
python run_server.py
```

## 🔧 Configuration

Edit `.env` file with your settings:

```env
# Database Configuration
DB_HOST=your-mysql-host
DB_PORT=3306
DB_NAME=your_totara_database
DB_USERNAME=your_username
DB_PASSWORD=your_password

# LLM Configuration  
LLM_MODEL=llama3.1:8b
OLLAMA_URL=http://localhost:11434

# Session Management
SESSION_TIMEOUT_MINUTES=60
CLEANUP_INTERVAL_MINUTES=10
```

## 🎯 Available Tools

The MCP server exposes these tools:

| Tool | Description | Usage |
|------|-------------|-------|
| `chat` | Main conversation interface | `chat(user_id="user123", message="Show my courses")` |
| `get_session_info` | Retrieve user session details | `get_session_info(user_id="user123")` |
| `get_system_stats` | System monitoring and statistics | `get_system_stats()` |
| `close_session` | Terminate user session | `close_session(user_id="user123")` |

## 📊 Example Usage

```python
# Example chat interaction
{
    "tool": "chat",
    "arguments": {
        "user_id": "student123",
        "message": "What courses am I enrolled in?"
    }
}

# Response
{
    "response": "You are currently enrolled in 3 courses: Python Programming, Data Science Fundamentals, and Machine Learning Basics. Your most recent enrollment was in Machine Learning Basics on Sept 15, 2025.",
    "sql_query": "SELECT c.fullname, ce.timeenrolled FROM courses c JOIN course_enrollments ce ON c.id = ce.courseid WHERE ce.userid = 123",
    "confidence": 0.95,
    "session_id": "sess_abc123"
}
```

## 🏫 Totara LMS Integration

Pre-configured support for common Totara LMS queries:

- **User Management**: Profile data, enrollment history
- **Course Information**: Available courses, completion status
- **Learning Plans**: Progress tracking, competency mapping  
- **Certifications**: Status, renewal requirements
- **Reporting**: Statistics, progress analytics

## 🔒 Security Features

- ✅ **Query Validation**: Only safe SELECT queries allowed
- ✅ **Parameter Sanitization**: SQL injection prevention
- ✅ **Session Isolation**: User data separation
- ✅ **Input Validation**: Message length and content limits
- ✅ **Error Handling**: Graceful failure management

## 📁 Project Structure

```
Haystack/
├── src/
│   ├── main.py                 # MCP server implementation
│   ├── config.py               # Configuration management
│   ├── database_connector.py   # MySQL/Totara integration
│   ├── haystack_pipeline.py    # Core Haystack pipeline
│   ├── session_manager.py      # Multi-user session handling
│   └── vector_store.py         # ChromaDB integration
├── test_demo.py                # Demo and testing
├── run_server.py               # Server startup script
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
└── README.md                  # This file
```

## 🧪 Testing

```bash
# Run the demo to verify installation
python test_demo.py

# Expected output: Architecture verification and chat examples
```

## 🚀 Deployment

For production deployment:

1. **Security**: Configure SSL, authentication, and firewall rules
2. **Performance**: Set up connection pooling and caching
3. **Monitoring**: Enable logging and health checks
4. **Scaling**: Consider load balancing for high traffic

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Haystack AI** for the excellent framework
- **Ollama** for local LLM deployment
- **ChromaDB** for vector storage capabilities
- **Totara Learning Solutions** for the LMS platform

## 📞 Support

For questions or support:
- 📧 Create an issue on GitHub
- 📖 Check the [SETUP.md](SETUP.md) guide
- 🔍 Review the demo code in `test_demo.py`

---

**Built with ❤️ for universities and educational institutions using Totara LMS**