# Totara LMS Chatbot - Haystack MCP Server

A sophisticated chatbot system built with Haystack framework and Model Context Protocol (MCP) for Totara LMS data interaction.

## Architecture

- **MCP Server**: Core server handling client connections
- **Haystack Pipeline**: LLM-powered query processing
- **MySQL Integration**: Direct access to Totara LMS database
- **Session Management**: Multi-user thread handling
- **ChromaDB**: Vector storage for enhanced context
- **LLM Brain**: llama3.1:8b orchestrating the entire flow

## Quick Start

1. Install dependencies:
```bash
pip install -e .
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Run the server:
```bash
python src/main.py
```

## Features

- Natural language to SQL query generation
- Session-based conversation handling
- Context-aware responses
- Totara LMS specific knowledge
- Multi-user support with thread isolation

## Configuration

See `.env.example` for required environment variables.