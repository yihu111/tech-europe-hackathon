# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based AI/ML API service that analyzes GitHub repositories to extract technical information about codebases, frameworks, and architecture patterns. Built with FastAPI and LangChain/LangGraph for a hackathon project.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the FastAPI development server
uvicorn main:app --reload

# Run on specific port
uvicorn main:app --reload --port 8000
```

## Architecture

The project implements a two-tier GitHub repository analysis system:

### Tier 1: Basic Analysis (`main.py`)
- FastAPI endpoints for GitHub repository discovery
- Dependency file parsing to detect frameworks
- Language detection via GitHub API
- Simple framework mapping based on dependencies

### Tier 2: Advanced AI Analysis (`knowledge_pipeline.py`)
- LangGraph-based map-reduce pipeline using OpenAI o4-mini
- Deep static and LLM-powered code analysis
- Concept extraction and architecture pattern recognition
- Designed for RAG system integration (vector search planned)

## Key Modules

- `main.py` - FastAPI application entry point with `/repos/{username}` endpoint
- `knowledge_pipeline.py` - Advanced LangGraph pipeline for deep codebase analysis
- `parsers.py` - Dependency file parsers (package.json, requirements.txt, etc.)
- `dependencies_data.py` - Language-to-dependency-file mappings
- `frameworks_data.py` - Framework detection rules by programming language
- `vector_search.py` - Placeholder for vector search functionality

## Environment Configuration

Requires `.env` file with:
- `OPENAI_API_KEY` - OpenAI API key for LLM functionality

## Framework Detection

Supports framework detection for:
- **Python**: FastAPI, Flask, Django, Pyramid, Tornado
- **JavaScript/TypeScript**: React, Vue, Angular, Next.js, Express, Gatsby

Framework detection works by parsing dependency files and matching against known framework signatures defined in `frameworks_data.py`.

## Current Development State

This is an active hackathon project. The basic GitHub analysis functionality is implemented, while the advanced AI pipeline framework is in place but may not be fully integrated with the API endpoints yet.