# Clarence

An AI-powered day trading execution agent built with Claude and Alpaca. Clarence scans the market for opportunities based on your risk appetite, presents trade recommendations with reasoning, and executes confirmed trades — all from your terminal.

> **WARNING: This software can execute real trades with real money.** By setting `ALPACA_PAPER_TRADE=False`, you enable live trading. You are solely responsible for any financial losses incurred. The author(s) of this project accept no responsibility or liability for any trading losses, damages, or financial harm resulting from the use of this software. Use at your own risk.

## How It Works

Clarence operates in two modes:

**Scan Mode** (`/scan`) — Automated opportunity discovery:
1. Fetches your account info and positions via the Alpaca MCP server
2. Discovers candidates using market screeners (most active stocks, top movers)
3. Scores each candidate on volume, spread, volatility, and momentum
4. Filters by your risk parameters (low / medium / high)
5. Sends candidates to Claude for trade analysis
6. Presents each opportunity for your approval, then executes via Alpaca

**Q&A Mode** (free-form) — Ask anything about your account or the market:
- "What are my current positions?"
- "What's the latest news on NVDA?"
- "Compare AAPL and MSFT financial metrics"

Claude routes your query through available tools (Alpaca MCP + Financial Datasets API), iterates until it has a complete answer, then responds.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- [Anthropic API key](https://console.anthropic.com/)
- [Alpaca API credentials](https://alpaca.markets/) (paper trading enabled by default)
- [Financial Datasets API key](https://financialdatasets.ai) (for news and metrics)

## Installation

```bash
git clone https://github.com/phin3has/clarence.git
cd clarence
uv sync
```

Set up your environment:

```bash
cp env.example .env
# Edit .env with your API keys
```

## Usage

```bash
uv run clarence
```

On first run, Clarence walks you through a quick onboarding (name + risk level).

### Commands

| Command | Description |
|---------|-------------|
| `/scan` | Scan for day trading opportunities |
| `/risk` | View or change your risk level |
| `/positions` | Show current positions |
| `/status` | Check API connections |
| `/help` | Show help menu |
| `exit` | Quit |

Anything else is treated as a free-form question sent to Claude with full tool access.

## Architecture

```
┌─────────────┐
│   CLI        │  prompt_toolkit async REPL
└──────┬──────┘
       │
┌──────▼──────┐
│   Agent      │  Two modes: scan() and run(query)
└──┬───────┬──┘
   │       │
┌──▼──┐ ┌──▼──────────┐
│Scan │ │ Q&A Loop     │
│Pipe │ │ (tool-use)   │
└──┬──┘ └──┬───────────┘
   │       │
┌──▼───────▼──┐     ┌──────────────────┐
│ Alpaca MCP   │     │ Financial         │
│ Server       │     │ Datasets API      │
│ (trading +   │     │ (news + metrics)  │
│  market data)│     └──────────────────┘
└──────────────┘
```

**Data sources:**
- **Alpaca MCP Server** — Account, positions, orders, quotes, bars, trades, order execution. Accessed via MCP protocol (`uvx alpaca-mcp-server`).
- **alpaca-py ScreenerClient** — Market discovery (most active stocks, top movers). Used locally since the MCP server lacks screener endpoints.
- **Financial Datasets API** — Company news and financial metrics. Local HTTP calls.

**Safety:**
- Paper trading enabled by default (`ALPACA_PAPER_TRADE=True`)
- Max 10 tool-call iterations per Q&A query
- Loop detection (aborts if same action repeats 3 times)
- Every trade requires explicit user approval

## Project Structure

```
src/clarence/
├── agent.py          # Two-mode async agent (scan + Q&A)
├── scanner.py        # Opportunity scanning pipeline
├── mcp_client.py     # Alpaca MCP server wrapper
├── model.py          # Anthropic Claude SDK interface
├── prompts.py        # System and task prompts
├── schemas.py        # Pydantic models
├── risk.py           # Risk levels and filtering
├── cli.py            # Async CLI entry point
├── tools/
│   ├── __init__.py   # Screener functions (alpaca-py)
│   └── finance/      # Financial Datasets API tools
│       ├── api.py    # HTTP helper
│       ├── news.py   # Company news
│       └── metrics.py# Financial metrics
└── utils/
    ├── profile.py    # User profile management
    ├── scoring.py    # Day trading scoring algorithm
    ├── help.py       # Help menu and status checks
    ├── ui.py         # Terminal UI (spinners, streaming)
    ├── intro.py      # Welcome message
    └── logger.py     # Logger
```

## Risk System

Three configurable risk levels control position sizing, stop losses, and candidate filtering:

| Parameter | Low | Medium | High |
|-----------|-----|--------|------|
| Max spread | 0.10% | 0.25% | 0.50% |
| Position size | 1-2% | 2-4% | 3-5% |
| Stop loss | 1% | 2% | 3% |
| Min volume | 1M | 500K | 200K |
| Min score | 70 | 55 | 40 |

Change your risk level at any time with `/risk`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

Keep pull requests small and focused.

## License

This project is licensed under the [MIT License](LICENSE).
