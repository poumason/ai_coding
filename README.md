# AI Coding

A multi-project playground for exploring AI agent technologies including Claude Code SDK, CrewAI, and LangGraph.

## Projects

This repository contains several demonstration and experimentation projects:

### 1. Claude Code Agent SDK (`cc_agent_sdk/`)

Examples and experiments using the Claude Agent SDK for building AI agent applications.

### 2. CrewAI Coffee Shop (`crewai_coffee_shop/`)

A complete CrewAI demonstration featuring a coffee shop use case with:
- Custom tools
- Multi-agent orchestration
- Knowledge management
- Test examples

### 3. LangGraph A2A Agent (`langgrapch/a2a/sample-agent/`)

A sample agent implementation using LangGraph with Agent-to-Agent (A2A) protocol support.

### 4. AG-UI Protocol Demo (`ag_ui_demo/`)

A FastAPI + Claude Agent SDK backend that speaks the [AG-UI protocol](https://ag-ui.com)
over SSE, with a small vanilla-JS frontend to watch streaming text, tool
calls, human-in-the-loop confirmation, and shared state sync as raw protocol
events.

### 5. Main Entry Point (`main.py`)

Simple CLI entry point for the project.

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Usage

Run the main entry point:

```bash
python main.py
```

## Dependencies

- `claude-agent-sdk>=0.1.53`
- `claude-code-sdk>=0.0.25`
- `fastapi`, `uvicorn`, `ag-ui-protocol` (for `ag_ui_demo/`)

## License

MIT