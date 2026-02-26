def print_intro():
    """Display the welcome screen with ASCII art."""
    LIGHT_BLUE = "\033[38;2;222;124;60m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    print("\n" * 2)

    box_width = 50
    welcome_text = "Welcome to Clarence"
    padding = (box_width - len(welcome_text) - 2) // 2

    print(f"{LIGHT_BLUE}{'=' * box_width}{RESET}")
    print(f"{LIGHT_BLUE}|{' ' * padding}{BOLD}{welcome_text}{RESET}{LIGHT_BLUE}{' ' * (box_width - len(welcome_text) - padding - 2)}|{RESET}")
    print(f"{LIGHT_BLUE}{'=' * box_width}{RESET}")
    print()

    clarence_art = f"""{BOLD}{LIGHT_BLUE}
 ██████╗██╗      █████╗ ██████╗ ███████╗███╗   ██╗ ██████╗███████╗
██╔════╝██║     ██╔══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝██╔════╝
██║     ██║     ███████║██████╔╝█████╗  ██╔██╗ ██║██║     █████╗
██║     ██║     ██╔══██║██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══╝
╚██████╗███████╗██║  ██║██║  ██║███████╗██║ ╚████║╚██████╗███████╗
 ╚═════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝ ╚═════╝╚══════╝
{RESET}"""

    print(clarence_art)
    print()
    print("Your day trading execution agent.")
    print("Type /scan to find opportunities, /help for commands, or ask any question.")
    print()
