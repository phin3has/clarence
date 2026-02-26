# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Clarence is a day trading execution agent built with Python. It scans the market for opportunities based on the user's risk appetite, presents trade recommendations, and executes confirmed trades via Alpaca. It operates in two modes: `/scan` for opportunity discovery and free-form Q&A for account/market queries.

## Development Commands

### Setup
```bash
# Install dependencies with uv package manager
uv sync

# Setup environment variables
cp env.example .env
# Then edit .env to add required API keys
```

### Running the Agent
```bash
# Run interactive CLI
uv run clarence
```

## Architecture Overview

### Two-Mode Async Agent

The agent (`src/clarence/agent.py`) operates in two modes:

1. **Scan Mode** (`/scan`): Runs the `OpportunityScanner` pipeline:
   - Fetch account info + positions via Alpaca MCP
   - Discover candidates via `alpaca-py` ScreenerClient (MCP lacks screener)
   - Score candidates on volume, spread, volatility, momentum
   - Filter by user's risk parameters
   - Generate recommendations via Claude
   - Present each opportunity, get user approval, execute via MCP

2. **Q&A Mode** (free-form queries): Simple tool-use loop:
   - Send query + all tools (MCP + local) to Claude
   - Route tool calls (MCP for Alpaca, local for Financial Datasets)
   - Iterate until Claude responds with text (max 10 steps)
   - Display answer

### MCP Integration

The `AlpacaMCPClient` (`src/clarence/mcp_client.py`) wraps the Alpaca MCP server:
- Spawns `uvx alpaca-mcp-server` as a subprocess
- Establishes `ClientSession` via `mcp` Python SDK
- Provides `get_tools()` for Anthropic API format tool definitions
- Routes `call_tool(name, args)` to the MCP session
- Tools include: account, positions, orders, quotes, bars, trades, order placement

### Risk System

The `risk.py` module defines three risk levels (low/medium/high) with parameters:
- Max spread %, position sizing %, stop loss %, min volume, volatility range, min score
- `filter_by_risk()` filters scored candidates
- `calculate_position_size()` and `calculate_stop_loss()` for trade sizing

### Hybrid Data Sources

**Alpaca MCP Server** — Real-time market data + trading:
- Account, positions, orders, quotes, bars, trades
- Order placement and cancellation
- Accessed via MCP protocol

**alpaca-py ScreenerClient** — Market discovery (local, not MCP):
- `get_most_active_stocks()`: High-volume stock discovery
- `get_top_movers()`: Top gainers and losers

**Financial Datasets API** — News + metrics (local HTTP calls):
- `get_news()`: Company news articles
- `get_financial_metrics_snapshot()`: Current financial metrics
- `get_financial_metrics()`: Historical financial metrics

### Safety Mechanisms

- **Step Limit**: Max 10 tool-call iterations per Q&A query
- **Loop Detection**: Tracks last 3 actions; aborts if identical action repeats 3 times
- **Error Handling**: Retry logic with exponential backoff for Anthropic API errors
- **Paper Trading**: Enabled by default via `ALPACA_PAPER_TRADE=True`

## Code Structure

### Core Files

- `src/clarence/agent.py`: Two-mode async agent (scan + Q&A)
- `src/clarence/scanner.py`: Opportunity scanning pipeline
- `src/clarence/mcp_client.py`: Alpaca MCP server wrapper
- `src/clarence/model.py`: Anthropic Claude SDK interface (async)
- `src/clarence/prompts.py`: System, scanning, opportunity, and answer prompts
- `src/clarence/schemas.py`: Pydantic models (Task, UserProfile, DayTradingMetrics, etc.)
- `src/clarence/risk.py`: Risk appetite parameters and filtering
- `src/clarence/cli.py`: Async CLI entry point with onboarding

### Tools

- `src/clarence/tools/__init__.py`: Screener functions (alpaca-py) + re-exports
- `src/clarence/tools/finance/api.py`: Financial Datasets API HTTP helper
- `src/clarence/tools/finance/news.py`: Company news retrieval
- `src/clarence/tools/finance/metrics.py`: Financial metrics snapshot + history

### Utilities

- `src/clarence/utils/profile.py`: Simple user profile (name, risk appetite)
- `src/clarence/utils/help.py`: Help menu and API status checking
- `src/clarence/utils/scoring.py`: Day trading scoring algorithm (volume, spread, volatility, momentum)
- `src/clarence/utils/ui.py`: Terminal UI (spinners, progress, streaming answer display)
- `src/clarence/utils/logger.py`: Logger wrapper around UI
- `src/clarence/utils/intro.py`: CLI welcome message with ASCII art

## Environment Variables

Required in `.env`:
- `ANTHROPIC_API_KEY`: Claude API key (required)
- `ALPACA_API_KEY`: Alpaca API key
- `ALPACA_SECRET_KEY`: Alpaca secret key
- `ALPACA_PAPER_TRADE`: `True` for paper, `False` for live (default: True)
- `FINANCIAL_DATASETS_API_KEY`: For news and financial metrics

## Important Notes

### Adding New Local Tools

1. Create function in `src/clarence/tools/` (plain Python, no decorators)
2. Add Anthropic-format tool definition in `agent.py` `local_tools` list
3. Add routing case in `agent.py` `_call_tool()` method

### Adding MCP Tools

MCP tools are discovered automatically via `mcp.get_tools()`. Any tool exposed by the Alpaca MCP server is automatically available to the agent.

### Prompts

All prompts in `prompts.py` are execution-focused:
- `SYSTEM_PROMPT`: Agent identity and capability awareness
- `SCANNING_PROMPT`: Candidate analysis with risk context
- `OPPORTUNITY_PROMPT`: Trade recommendation presentation
- `ANSWER_PROMPT`: Data-focused Q&A responses

### CLI Commands

- `/scan` — Scan for opportunities
- `/risk` — View/change risk level
- `/positions` — Show current positions
- `/status` — Check API connections
- `/help` — Help menu
- `exit` — Quit
