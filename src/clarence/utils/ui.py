import sys
import time
import threading
from contextlib import contextmanager
from typing import Optional, Callable, Iterator
from functools import wraps


class Colors:
    BLUE = "\033[38;2;222;124;60m"  # Claude Orange
    CYAN = "\033[38;2;255;165;0m"   # Lighter orange for contrast
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    WHITE = "\033[97m"
    LIGHT_BLUE = "\033[38;2;222;124;60m"  # Same as CLARENCE ASCII art (Claude Orange)


class Spinner:
    """An animated spinner that runs in a separate thread."""
    
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(self, message: str = "", color: str = Colors.CYAN):
        self.message = message
        self.color = color
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
    def _animate(self):
        """Animation loop that runs in a separate thread."""
        idx = 0
        while self.running:
            frame = self.FRAMES[idx % len(self.FRAMES)]
            sys.stdout.write(f"\r{self.color}{frame}{Colors.ENDC} {self.message}")
            sys.stdout.flush()
            time.sleep(0.08)
            idx += 1
    
    def start(self):
        """Start the spinner animation."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._animate, daemon=True)
            self.thread.start()
    
    def stop(self, final_message: str = "", symbol: str = "✓", symbol_color: str = Colors.GREEN):
        """Stop the spinner and optionally show a completion message."""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()
            # Clear the line
            sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
            if final_message:
                print(f"{symbol_color}{symbol}{Colors.ENDC} {final_message}")
            sys.stdout.flush()
    
    def update_message(self, message: str):
        """Update the spinner message."""
        self.message = message


def show_progress(message: str, success_message: str = ""):
    """Decorator to show progress spinner while a function executes."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            spinner = Spinner(message, color=Colors.CYAN)
            spinner.start()
            try:
                result = func(*args, **kwargs)
                spinner.stop(success_message or message.replace("...", " ✓"), symbol="✓", symbol_color=Colors.GREEN)
                return result
            except KeyboardInterrupt:
                spinner.stop("", symbol="", symbol_color="")
                raise
            except Exception as e:
                spinner.stop(f"Failed: {str(e)}", symbol="✗", symbol_color=Colors.RED)
                raise
        return wrapper
    return decorator


class UI:
    """Interactive UI for displaying agent progress and results."""
    
    def __init__(self):
        self.current_spinner: Optional[Spinner] = None
        
    @contextmanager
    def progress(self, message: str, success_message: str = ""):
        """Context manager for showing progress with a spinner."""
        spinner = Spinner(message, color=Colors.CYAN)
        self.current_spinner = spinner
        spinner.start()
        try:
            yield spinner
            spinner.stop(success_message or message.replace("...", " ✓"), symbol="✓", symbol_color=Colors.GREEN)
        except KeyboardInterrupt:
            spinner.stop("", symbol="", symbol_color="")
            raise
        except Exception as e:
            spinner.stop(f"Failed: {str(e)}", symbol="✗", symbol_color=Colors.RED)
            raise
        finally:
            self.current_spinner = None
    
    def print_header(self, text: str):
        """Print a section header."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}╭─ {text}{Colors.ENDC}")
    
    def print_user_query(self, query: str):
        """Print the user's query in the same style as DEXTER ASCII art."""
        print(f"\n{Colors.BOLD}{Colors.LIGHT_BLUE}You: {query}{Colors.ENDC}\n")
    
    def print_task_list(self, tasks):
        """Print a clean list of planned tasks."""
        if not tasks:
            return
        self.print_header("Planned Tasks")
        for i, task in enumerate(tasks):
            status = "+"
            color = Colors.DIM
            desc = task.get('description', task)
            print(f"{Colors.BLUE}│{Colors.ENDC} {color}{status}{Colors.ENDC} {desc}")
        print(f"{Colors.BLUE}╰{'─' * 50}{Colors.ENDC}\n")
    
    def print_task_start(self, task_desc: str):
        """Print when starting a task."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}▶ Task:{Colors.ENDC} {task_desc}")
    
    def print_task_done(self, task_desc: str):
        """Print when a task is completed."""
        print(f"{Colors.GREEN}  ✓ Completed{Colors.ENDC} {Colors.DIM}│ {task_desc}{Colors.ENDC}")
    
    def print_tool_params(self, params: str):
        """Print tool parameters before execution."""
        params_display = f" {Colors.DIM}{params}{Colors.ENDC}" if params and len(params) > 0 else ""
        print(f"  {Colors.MAGENTA}→{Colors.ENDC}  Parameters: {params_display}")

    def print_insight_prefix(self):
        """Print prefix for mid-execution insights."""
        print(f"\n  {Colors.YELLOW}💡{Colors.ENDC} ", end="")
    
    def print_tool_run(self, result: str):
        """Print when a tool is executed."""
        result_display = f" {Colors.DIM}({result[:150]}...){Colors.ENDC}" if result and len(result) > 0 else ""
        print(f"  {Colors.YELLOW}⚡{Colors.ENDC} Result: {result_display}")
    
    def print_answer(self, answer: str):
        """Print the final answer in a beautiful box."""
        width = 80
        
        # Top border
        print(f"\n{Colors.BOLD}{Colors.BLUE}╔{'═' * (width - 2)}╗{Colors.ENDC}")
        
        # Title
        title = "ANSWER"
        padding = (width - len(title) - 2) // 2
        print(f"{Colors.BOLD}{Colors.BLUE}║{' ' * padding}{title}{' ' * (width - len(title) - padding - 2)}║{Colors.ENDC}")
        
        # Separator
        print(f"{Colors.BLUE}╠{'═' * (width - 2)}╣{Colors.ENDC}")
        
        # Answer content with proper line wrapping
        print(f"{Colors.BLUE}║{Colors.ENDC}{' ' * (width - 2)}{Colors.BLUE}║{Colors.ENDC}")
        for line in answer.split('\n'):
            if len(line) == 0:
                print(f"{Colors.BLUE}║{Colors.ENDC}{' ' * (width - 2)}{Colors.BLUE}║{Colors.ENDC}")
            else:
                # Word wrap long lines
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= width - 6:
                        current_line += word + " "
                    else:
                        if current_line:
                            print(f"{Colors.BLUE}║{Colors.ENDC} {current_line.ljust(width - 4)} {Colors.BLUE}║{Colors.ENDC}")
                        current_line = word + " "
                if current_line:
                    print(f"{Colors.BLUE}║{Colors.ENDC} {current_line.ljust(width - 4)} {Colors.BLUE}║{Colors.ENDC}")
        
        print(f"{Colors.BLUE}║{Colors.ENDC}{' ' * (width - 2)}{Colors.BLUE}║{Colors.ENDC}")
        
        # Bottom border
        print(f"{Colors.BOLD}{Colors.BLUE}╚{'═' * (width - 2)}╝{Colors.ENDC}\n")
    
    async def async_stream_answer(self, async_text_chunks) -> str:
        """Stream answer from an async iterator and display in a box."""
        width = 80

        print(f"\n{Colors.BOLD}{Colors.BLUE}\u2554{'═' * (width - 2)}\u2557{Colors.ENDC}")
        title = "ANSWER"
        padding = (width - len(title) - 2) // 2
        print(f"{Colors.BOLD}{Colors.BLUE}\u2551{' ' * padding}{title}{' ' * (width - len(title) - padding - 2)}\u2551{Colors.ENDC}")
        print(f"{Colors.BLUE}\u2560{'═' * (width - 2)}\u2563{Colors.ENDC}")
        print(f"{Colors.BLUE}\u2551{Colors.ENDC}", end="", flush=True)

        accumulated_text = ""
        current_line = ""

        try:
            async for chunk in async_text_chunks:
                accumulated_text += chunk
                for char in chunk:
                    if char == '\n':
                        padding_needed = max(0, width - 4 - len(current_line))
                        print(f" {current_line}{' ' * padding_needed} {Colors.BLUE}\u2551{Colors.ENDC}")
                        print(f"{Colors.BLUE}\u2551{Colors.ENDC}", end="", flush=True)
                        current_line = ""
                    else:
                        current_line += char
                        if len(current_line) >= width - 6:
                            last_space = current_line.rfind(' ', 0, width - 6)
                            if last_space > 0:
                                line_to_print = current_line[:last_space]
                                padding_needed = width - 4 - len(line_to_print)
                                print(f" {line_to_print}{' ' * padding_needed} {Colors.BLUE}\u2551{Colors.ENDC}")
                                print(f"{Colors.BLUE}\u2551{Colors.ENDC}", end="", flush=True)
                                current_line = current_line[last_space + 1:]
                            else:
                                line_to_print = current_line[:width - 6]
                                padding_needed = width - 4 - len(line_to_print)
                                print(f" {line_to_print}{' ' * padding_needed} {Colors.BLUE}\u2551{Colors.ENDC}")
                                print(f"{Colors.BLUE}\u2551{Colors.ENDC}", end="", flush=True)
                                current_line = current_line[width - 6:]

            if current_line:
                padding_needed = max(0, width - 4 - len(current_line))
                print(f" {current_line}{' ' * padding_needed} {Colors.BLUE}\u2551{Colors.ENDC}")
            else:
                print(f"{' ' * (width - 2)}{Colors.BLUE}\u2551{Colors.ENDC}")
        except Exception:
            if current_line:
                padding_needed = max(0, width - 4 - len(current_line))
                print(f" {current_line}{' ' * padding_needed} {Colors.BLUE}\u2551{Colors.ENDC}")
            else:
                print(f"{' ' * (width - 2)}{Colors.BLUE}\u2551{Colors.ENDC}")
            raise

        print(f"{Colors.BLUE}\u2551{Colors.ENDC}{' ' * (width - 2)}{Colors.BLUE}\u2551{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.BLUE}\u255a{'═' * (width - 2)}\u255d{Colors.ENDC}\n")

        return accumulated_text

    def stream_answer(self, text_chunks: Iterator[str]) -> str:
        """
        Stream answer text chunks and display them in a beautiful box.
        Returns the complete accumulated text.
        """
        width = 80
        
        # Top border
        print(f"\n{Colors.BOLD}{Colors.BLUE}╔{'═' * (width - 2)}╗{Colors.ENDC}")
        
        # Title
        title = "ANSWER"
        padding = (width - len(title) - 2) // 2
        print(f"{Colors.BOLD}{Colors.BLUE}║{' ' * padding}{title}{' ' * (width - len(title) - padding - 2)}║{Colors.ENDC}")
        
        # Separator
        print(f"{Colors.BLUE}╠{'═' * (width - 2)}╣{Colors.ENDC}")
        
        # Start content area - print first line border
        print(f"{Colors.BLUE}║{Colors.ENDC}", end="", flush=True)
        
        accumulated_text = ""
        current_line = ""
        
        try:
            for chunk in text_chunks:
                accumulated_text += chunk
                
                # Process chunk character by character
                for char in chunk:
                    if char == '\n':
                        # Print current line with proper padding and border
                        padding_needed = max(0, width - 4 - len(current_line))
                        print(f" {current_line}{' ' * padding_needed} {Colors.BLUE}║{Colors.ENDC}")
                        # Start next line
                        print(f"{Colors.BLUE}║{Colors.ENDC}", end="", flush=True)
                        current_line = ""
                    else:
                        current_line += char
                        
                        # Check if line needs wrapping (simple word wrap)
                        if len(current_line) >= width - 6:
                            # Try to find last space for word wrap
                            last_space = current_line.rfind(' ', 0, width - 6)
                            if last_space > 0:
                                # Wrap at word boundary
                                line_to_print = current_line[:last_space]
                                padding_needed = width - 4 - len(line_to_print)
                                print(f" {line_to_print}{' ' * padding_needed} {Colors.BLUE}║{Colors.ENDC}")
                                print(f"{Colors.BLUE}║{Colors.ENDC}", end="", flush=True)
                                current_line = current_line[last_space + 1:]
                            else:
                                # No space found, wrap at character boundary
                                line_to_print = current_line[:width - 6]
                                padding_needed = width - 4 - len(line_to_print)
                                print(f" {line_to_print}{' ' * padding_needed} {Colors.BLUE}║{Colors.ENDC}")
                                print(f"{Colors.BLUE}║{Colors.ENDC}", end="", flush=True)
                                current_line = current_line[width - 6:]
            
            # Print any remaining content on the current line
            if current_line:
                padding_needed = max(0, width - 4 - len(current_line))
                print(f" {current_line}{' ' * padding_needed} {Colors.BLUE}║{Colors.ENDC}")
            else:
                # Empty line at end
                print(f"{' ' * (width - 2)}{Colors.BLUE}║{Colors.ENDC}")
        except Exception as e:
            # On error, print remaining content
            if current_line:
                padding_needed = max(0, width - 4 - len(current_line))
                print(f" {current_line}{' ' * padding_needed} {Colors.BLUE}║{Colors.ENDC}")
            else:
                print(f"{' ' * (width - 2)}{Colors.BLUE}║{Colors.ENDC}")
            raise
        
        # Bottom border
        print(f"{Colors.BLUE}║{Colors.ENDC}{' ' * (width - 2)}{Colors.BLUE}║{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.BLUE}╚{'═' * (width - 2)}╝{Colors.ENDC}\n")
        
        return accumulated_text
    
    def print_info(self, message: str):
        """Print an info message."""
        print(f"{Colors.DIM}{message}{Colors.ENDC}")
    
    def print_error(self, message: str):
        """Print an error message."""
        print(f"{Colors.RED}✗ Error:{Colors.ENDC} {message}")
    
    def print_warning(self, message: str):
        """Print a warning message."""
        print(f"{Colors.YELLOW}⚠ Warning:{Colors.ENDC} {message}")

