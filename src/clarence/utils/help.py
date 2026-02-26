"""Help menu and status checking for Clarence."""
import os
from clarence.utils.ui import Colors


def show_help_menu():
    ORANGE = Colors.BLUE
    RESET = Colors.ENDC
    BOLD = Colors.BOLD

    help_text = f"""
{BOLD}{ORANGE}============================================================
                     CLARENCE HELP MENU
============================================================{RESET}

{BOLD}COMMANDS:{RESET}
  {ORANGE}/scan{RESET}       - Scan market for day trading opportunities
  {ORANGE}/risk{RESET}       - View or change your risk level
  {ORANGE}/positions{RESET}  - Show current positions
  {ORANGE}/status{RESET}     - Check API connection status
  {ORANGE}/help{RESET}       - Show this menu
  {ORANGE}exit{RESET}        - Exit Clarence

{BOLD}HOW /scan WORKS:{RESET}
  1. Checks your account and buying power
  2. Scans market for active stocks and top movers
  3. Scores candidates on volume, spread, volatility, momentum
  4. Filters by your risk level
  5. Presents recommendations with reasoning
  6. You confirm (yes/no/modify) before any trade executes

{BOLD}RISK LEVELS:{RESET}
  Low    - Min score 70, tight spreads, high volume only
  Medium - Min score 55, balanced filters
  High   - Min score 40, wider stops, more volatile stocks

{BOLD}FREE-FORM QUERIES:{RESET}
  Ask anything about your account, positions, or market data:
  - "What's my buying power?"
  - "Get a quote for TSLA"
  - "Show me AAPL news"
  - "Place a limit order for 10 shares of NVDA at $140"

{BOLD}TIPS:{RESET}
  - Run /scan during market hours for best results
  - Press Ctrl+C to cancel any operation
  - Paper trading is ON by default (set ALPACA_PAPER_TRADE=False for live)
"""
    print(help_text)


def show_status():
    ORANGE = Colors.BLUE
    RESET = Colors.ENDC
    BOLD = Colors.BOLD

    print(f"\n{BOLD}{ORANGE}API CONNECTION STATUS{RESET}\n")

    # Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    status = "Configured" if anthropic_key else "Not configured"
    print(f"  Anthropic:           {status}")

    # Alpaca
    alpaca_key = os.getenv("ALPACA_API_KEY")
    alpaca_secret = os.getenv("ALPACA_SECRET_KEY")
    paper = os.getenv("ALPACA_PAPER_TRADE", "True").lower() in ("true", "1", "yes")
    if alpaca_key and alpaca_secret:
        mode = "Paper" if paper else "LIVE"
        print(f"  Alpaca:              Configured ({mode} trading)")
    else:
        print(f"  Alpaca:              Not configured")

    # Financial Datasets
    fd_key = os.getenv("FINANCIAL_DATASETS_API_KEY")
    status = "Configured" if fd_key else "Not configured"
    print(f"  Financial Datasets:  {status}")

    print()
