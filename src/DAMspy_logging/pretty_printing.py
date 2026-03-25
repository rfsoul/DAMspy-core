# DAMspy_logging/pretty_printing.py
# Unified console output utilities for DAMSpy
# -------------------------------------------------
# SECTION 1: Low-level render primitives (coloured output)
# SECTION 2: High-level semantic helpers (headers, success, etc.)
# -------------------------------------------------

# ====== SECTION 1: Raw colour printing (rendering layer) ======
def print_blue(msg: str):   print(f"\033[94m{msg}\033[0m")
def print_green(msg: str):  print(f"\033[92m{msg}\033[0m")
def print_yellow(msg: str): print(f"\033[93m{msg}\033[0m")
def print_red(msg: str):    print(f"\033[91m{msg}\033[0m")
def print_white(msg: str):  print(msg)


# ====== SECTION 2: Semantic “pretty printing” functions ======
_SEP = "=" * 60

def header(title: str):
    """Section title with separators (blue)."""
    print_blue("\n" + _SEP)
    print_blue(title)
    print_blue(_SEP + "\n")

def line(msg: str):
    """Standard informational message (white)."""
    print_white(str(msg))

def success(msg: str):
    """Highlight successful completion."""
    print_green(str(msg))

def warning(msg: str):
    """Show warning/caution messages."""
    print_yellow(str(msg))

def error(msg: str):
    """Display failure or error messages."""
    print_red(str(msg))

#section3 textformatter stuff
# --- User I/O helpers (from old text_formatter) ---
import time
import msvcrt

def get_timestamp():
    return time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())

def _flush_kbd():
    # PyCharm tip: enable "Emulate terminal in output console" in Run/Debug config
    while msvcrt.kbhit():
        msvcrt.getch()

def my_input(msg: str):
    _flush_kbd()
    print_yellow(str(msg),)  # show prompt in yellow
    print_white("",)         # ensure a trailing space-like separation if desired
    return input()

def message(msg: str):
    return my_input(msg)

def question(msg: str):
    _flush_kbd()
    ans = my_input(str(msg) + ' [y/n]').lower()
    while True:
        if ans in ('y', ""):
            return True
        elif ans == 'n':
            return False
        else:
            ans = my_input("Please respond with 'y' or 'n':").lower()
