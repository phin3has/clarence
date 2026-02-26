import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class AlpacaMCPClient:
    """Wrapper around the Alpaca MCP server for tool discovery and execution."""

    def __init__(self):
        self.session: ClientSession | None = None
        self._client_cm = None
        self._session_cm = None

    async def connect(self):
        """Spawn the alpaca-mcp-server subprocess and establish a session."""
        # Start with parent environment. Only override ALPACA vars if they
        # have actual values — empty strings block load_dotenv from reading
        # the .env file (dotenv defaults to override=False).
        env = dict(os.environ)
        for key in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY", "ALPACA_PAPER_TRADE"):
            val = os.getenv(key)
            if val:
                env[key] = val

        # Pass absolute path to .env so the server finds credentials
        # regardless of subprocess working directory
        env_file = os.path.join(os.getcwd(), ".env")
        args = ["alpaca-mcp-server", "serve"]
        if os.path.exists(env_file):
            args.extend(["--config-file", os.path.abspath(env_file)])

        server_params = StdioServerParameters(
            command="uvx",
            args=args,
            env=env,
        )

        self._client_cm = stdio_client(server_params)
        read_stream, write_stream = await self._client_cm.__aenter__()

        self._session_cm = ClientSession(read_stream, write_stream)
        self.session = await self._session_cm.__aenter__()
        await self.session.initialize()

    async def get_tools(self) -> list[dict]:
        """Return tool definitions formatted for the Anthropic API."""
        if not self.session:
            return []

        result = await self.session.list_tools()
        tools = []
        for tool in result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            })
        return tools

    async def call_tool(self, name: str, args: dict) -> str:
        """Execute an MCP tool and return the text result."""
        if not self.session:
            return json.dumps({"error": "MCP session not connected"})

        result = await self.session.call_tool(name, args)
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts) if parts else json.dumps({"result": "ok"})

    async def disconnect(self):
        """Cleanly shut down the MCP session and subprocess."""
        if self._session_cm:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception:
                pass
        if self._client_cm:
            try:
                await self._client_cm.__aexit__(None, None, None)
            except Exception:
                pass
        self.session = None
