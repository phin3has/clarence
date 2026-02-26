import json
from datetime import datetime

from clarence.mcp_client import AlpacaMCPClient
from clarence.model import call_llm, call_llm_stream
from clarence.prompts import get_system_prompt, ANSWER_PROMPT
from clarence.risk import get_risk_parameters, RiskParameters
from clarence.scanner import OpportunityScanner
from clarence.utils.logger import Logger


class Agent:
    """Two-mode async agent: /scan for opportunities, free-form for Q&A."""

    def __init__(self, mcp: AlpacaMCPClient, risk_level: str = "medium"):
        self.mcp = mcp
        self.risk_level = risk_level
        self.risk_params = get_risk_parameters(risk_level)
        self.logger = Logger()

    async def scan(self):
        """Scan for day trading opportunities, present them, and execute confirmed trades."""
        scanner = OpportunityScanner(self.mcp, self.risk_params, self.logger)
        recommendations = await scanner.scan()

        if not recommendations:
            self.logger._log("No opportunities found matching your risk profile.")
            return

        self.logger._log(f"\nFound {len(recommendations)} opportunities:\n")

        for rec in recommendations:
            # Present the opportunity
            await scanner.present_opportunity(rec)

            # Get user approval
            approval = await _get_user_approval(rec)

            if approval == "yes":
                self.logger._log(f"\nPlacing order for {rec.quantity} shares of {rec.symbol}...")
                result = await scanner.execute_trade(rec, rec.quantity, rec.limit_price)
                self.logger._log(f"Order result: {result}\n")
            elif approval == "skip":
                self.logger._log(f"Skipped {rec.symbol}.\n")
                continue
            elif isinstance(approval, dict):
                qty = approval.get("quantity", rec.quantity)
                price = approval.get("price", rec.limit_price)
                self.logger._log(f"\nPlacing modified order: {qty} shares of {rec.symbol} @ ${price}...")
                result = await scanner.execute_trade(rec, qty, price)
                self.logger._log(f"Order result: {result}\n")

    async def run(self, query: str):
        """Q&A loop: send query + tools to Claude, route tool calls, iterate."""
        self.logger.ui.print_user_query(query)

        # Build tool list from MCP
        mcp_tools = await self.mcp.get_tools()

        # Add local finance tools as Anthropic-format tool definitions
        local_tools = [
            {
                "name": "get_news",
                "description": "Retrieve recent news articles for a stock ticker.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        "limit": {"type": "integer", "description": "Number of articles (default 5)"},
                    },
                    "required": ["ticker"],
                },
            },
            {
                "name": "get_financial_metrics_snapshot",
                "description": "Fetch current financial metrics snapshot for a company (P/E, market cap, etc).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    },
                    "required": ["ticker"],
                },
            },
            {
                "name": "get_financial_metrics",
                "description": "Retrieve historical financial metrics for a company.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        "period": {"type": "string", "description": "Period: annual, quarterly, or ttm"},
                        "limit": {"type": "integer", "description": "Number of records"},
                    },
                    "required": ["ticker"],
                },
            },
        ]

        all_tools = mcp_tools + local_tools

        messages = [{"role": "user", "content": query}]
        system = get_system_prompt()

        last_actions = []
        max_steps = 10

        for step in range(max_steps):
            response = await call_llm(messages=messages, system=system, tools=all_tools)

            # If Claude responded with text only, we're done
            if response.stop_reason == "end_turn":
                text = _extract_text(response)
                if text:
                    self.logger.ui.print_answer(text)
                return

            # Process tool calls
            tool_blocks = [b for b in response.content if b.type == "tool_use"]
            if not tool_blocks:
                text = _extract_text(response)
                if text:
                    self.logger.ui.print_answer(text)
                return

            # Append assistant message
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call
            tool_results = []
            for block in tool_blocks:
                tool_name = block.name
                tool_input = block.input

                # Loop detection
                action_sig = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
                last_actions.append(action_sig)
                if len(last_actions) > 3:
                    last_actions = last_actions[-3:]
                if len(set(last_actions)) == 1 and len(last_actions) == 3:
                    self.logger._log("Detected repeating action loop — stopping.")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Error: Action loop detected. Please try a different approach.",
                    })
                    continue

                # Route tool call
                result_text = await self._call_tool(tool_name, tool_input)
                self.logger.ui.print_tool_params(f"{tool_name}({json.dumps(tool_input)})")
                self.logger.ui.print_tool_run(result_text[:200] if result_text else "")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

            messages.append({"role": "user", "content": tool_results})

        # Max steps reached — ask Claude to summarize what it has
        messages.append({
            "role": "user",
            "content": "Maximum tool calls reached. Please summarize what you've found so far.",
        })
        response = await call_llm(messages=messages, system=system)
        text = _extract_text(response)
        if text:
            self.logger.ui.print_answer(text)

    async def _call_tool(self, name: str, args: dict) -> str:
        """Route a tool call to MCP or local functions."""
        if name == "get_news":
            from clarence.tools.finance.news import get_news
            result = get_news(
                ticker=args.get("ticker", ""),
                limit=args.get("limit", 5),
            )
            return json.dumps(result, default=str)

        if name == "get_financial_metrics_snapshot":
            from clarence.tools.finance.metrics import get_financial_metrics_snapshot
            result = get_financial_metrics_snapshot(ticker=args.get("ticker", ""))
            return json.dumps(result, default=str)

        if name == "get_financial_metrics":
            from clarence.tools.finance.metrics import get_financial_metrics
            result = get_financial_metrics(
                ticker=args.get("ticker", ""),
                period=args.get("period", "ttm"),
                limit=args.get("limit", 4),
            )
            return json.dumps(result, default=str)

        # Default: route to MCP
        return await self.mcp.call_tool(name, args)


def _extract_text(response) -> str:
    """Extract text content from an Anthropic Message response."""
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


async def _get_user_approval(rec) -> str | dict:
    """Interactive approval prompt for a trade recommendation."""
    from prompt_toolkit import PromptSession
    session = PromptSession()

    while True:
        try:
            answer = await session.prompt_async(">> ")
            answer = answer.strip().lower()
        except (KeyboardInterrupt, EOFError):
            return "skip"

        if answer in ("yes", "y"):
            return "yes"
        if answer in ("no", "n", "skip", "pass"):
            return "skip"
        if answer.startswith("modify") or answer.startswith("mod"):
            print(f"  Current: {rec.quantity} shares @ ${rec.limit_price}")
            try:
                qty_input = await session.prompt_async("  New quantity (Enter to keep): ")
                price_input = await session.prompt_async("  New price (Enter to keep): ")
                qty = int(qty_input) if qty_input.strip() else rec.quantity
                price = float(price_input) if price_input.strip() else rec.limit_price
                return {"quantity": qty, "price": price}
            except (ValueError, KeyboardInterrupt, EOFError):
                return "skip"

        print("Enter 'yes', 'no', or 'modify'")
