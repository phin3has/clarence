import asyncio
from dotenv import load_dotenv

load_dotenv()

from clarence.agent import Agent
from clarence.mcp_client import AlpacaMCPClient
from clarence.risk import get_risk_parameters, RISK_LEVELS
from clarence.utils.intro import print_intro
from clarence.utils.profile import ProfileManager
from clarence.utils.help import show_help_menu, show_status
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory


def run_onboarding(profile_manager: ProfileManager) -> dict:
    """Simple onboarding: name + risk appetite."""
    print("\n" + "=" * 50)
    print("Welcome to Clarence! Let's get you set up.")
    print("=" * 50 + "\n")

    name = input("What's your name? ")
    print(f"\nGood to meet you, {name}!\n")

    print("What's your risk appetite?")
    print("1. Low    (tight stops, high-volume stocks only)")
    print("2. Medium (balanced risk/reward)")
    print("3. High   (wider stops, more volatile stocks)")

    while True:
        choice = input("\nEnter 1, 2, or 3: ").strip()
        if choice in ("1", "2", "3"):
            risk = {"1": "low", "2": "medium", "3": "high"}[choice]
            break
        print("Please enter 1, 2, or 3")

    profile = profile_manager._create_default_profile()
    profile["name"] = name
    profile["risk_appetite"] = risk
    profile_manager.save_profile(profile)

    print(f"\nProfile created! Risk level: {risk}")
    print("Type /scan to find opportunities or ask any trading question.\n")

    return profile


async def async_main():
    profile_manager = ProfileManager()
    profile = profile_manager.load_or_create_profile()

    if not profile.get("name"):
        profile = run_onboarding(profile_manager)

    print_intro()
    show_status()

    # Connect to Alpaca MCP server
    mcp = AlpacaMCPClient()
    print("Connecting to Alpaca MCP server...")
    try:
        await mcp.connect()
        print("Connected to Alpaca MCP server.\n")
    except Exception as e:
        print(f"Warning: Could not connect to Alpaca MCP server: {e}")
        print("Trading features will be unavailable. Check that 'uvx alpaca-mcp-server' is installed.\n")

    agent = Agent(mcp=mcp, risk_level=profile.get("risk_appetite", "medium"))

    session = PromptSession(history=InMemoryHistory())

    try:
        while True:
            try:
                query = await session.prompt_async(">> ")
                query = query.strip()

                if not query:
                    continue

                if query.lower() in ("exit", "quit"):
                    break

                if query.lower() in ("help", "/help"):
                    show_help_menu()
                    continue

                if query.lower() in ("status", "/status"):
                    show_status()
                    continue

                if query.lower() in ("scan", "/scan"):
                    try:
                        await agent.scan()
                    except KeyboardInterrupt:
                        print("\nScan cancelled.\n")
                    continue

                if query.lower() in ("risk", "/risk"):
                    current = profile.get("risk_appetite", "medium")
                    print(f"\nCurrent risk level: {current}")
                    print("1. Low  2. Medium  3. High")
                    try:
                        choice = await session.prompt_async("New level (Enter to keep): ")
                        choice = choice.strip()
                        if choice in ("1", "2", "3"):
                            new_risk = {"1": "low", "2": "medium", "3": "high"}[choice]
                            profile["risk_appetite"] = new_risk
                            profile_manager.save_profile(profile)
                            agent.risk_level = new_risk
                            agent.risk_params = get_risk_parameters(new_risk)
                            print(f"Risk level updated to: {new_risk}\n")
                        else:
                            print(f"Keeping: {current}\n")
                    except (KeyboardInterrupt, EOFError):
                        print(f"Keeping: {current}\n")
                    continue

                if query.lower() in ("positions", "/positions"):
                    try:
                        result = await mcp.call_tool("get_all_positions", {})
                        print(f"\n{result}\n")
                    except Exception as e:
                        print(f"\nCould not fetch positions: {e}\n")
                    continue

                # Free-form query
                try:
                    await agent.run(query)
                except KeyboardInterrupt:
                    print("\nCancelled. Ask a new question or Ctrl+C to quit.\n")

            except (KeyboardInterrupt, EOFError):
                break
    finally:
        # Update session count
        profile["session_count"] = profile.get("session_count", 0) + 1
        profile_manager.save_profile(profile)

        await mcp.disconnect()
        print(f"\nGoodbye, {profile.get('name', 'trader')}!\n")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
