#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"
TOOLS_DIR.mkdir(parents=True, exist_ok=True)

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    import network_tools as net
except ImportError as exc:
    net = None
    NETWORK_IMPORT_ERROR = exc
else:
    NETWORK_IMPORT_ERROR = None

try:
    import file_tools as ft
except ImportError as exc:
    ft = None
    FILE_IMPORT_ERROR = exc
else:
    FILE_IMPORT_ERROR = None

try:
    from colorama import Fore, Style, just_fix_windows_console
    just_fix_windows_console()
except ImportError:
    class _NoColor:
        def __getattr__(self, name):
            return ""

    Fore = Style = _NoColor()

title = "GrasshoppeR"

RST = "\033[0m"

DIM = "\033[2;37m"
PROMPT = "\033[1;32m"
ALERT = "\033[1;31m"
BOLD = "\033[1m"

THEMES = {
    "red": ("\033[1;31m", "\033[31m"),
    "green": ("\033[1;32m", "\033[32m"),
    "white": ("\033[1;37m", "\033[37m"),
}

FONT = {
    " ": ("  ", "  "),
    "A": ("█▀█", "█▀█"),
    "B": ("█▄▄", "█▄█"),
    "C": ("█▀▀", "█▄▄"),
    "D": ("█▀▄", "█▄▀"),
    "E": ("█▀▀", "██▄"),
    "F": ("█▀▀", "█▀ "),
    "G": ("█▀▀", "█▄█"),
    "H": ("█   █", "█▀█"),
    "I": ("█", "█"),
    "J": ("  █", "█▄█"),
    "K": ("█▄▀", "█ █"),
    "L": ("█  ", "█▄▄"),
    "M": ("█▀▄▀█", "█ ▀ █"),
    "N": ("█▄ █", "█ ▀█"),
    "O": ("█▀█", "█▄█"),
    "P": ("█▀█", "█▀▀"),
    "Q": ("█▀█", "▀▀█"),
    "R": ("█▀█", "█▀▄"),
    "S": ("█▀", "▄█"),
    "T": ("▀█▀", "   █   "),
    "U": ("█ 𓆧█", "█▄▄█"),
    "V": ("█ █", "▀▄▀"),
    "W": ("█ █ █", "▀▄▀▄▀"),
    "X": ("▀▄▀", "█ █"),
    "Y": ("█▄█", " █ "),
    "Z": ("▀█", "█▄"),
}

PROMPT = "\033[1;32m"
RST = "\033[0m"

def banner():
    text = "GRASSHOPPER SUITE"

    line1 = ""
    line2 = ""

    for char in text.upper():
        top, bottom = FONT.get(char, FONT[" "])
        line1 += top + " "
        line2 += bottom + " "

    print(f"""
{PROMPT}{line1}
{line2}{RST}
""")

banner()
BANNER = rf"""
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢁⣴⣧⠄⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢀⢁⢄⠅⠤⠅⢴⣿⣿⣿⣷⣕⠤⠅⠤⢅⢄⢁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢕⠍⠉⠁⠁⠀⠁⠀⢱⣿⣿⠟⠛⢿⣿⣅⠁⠀⠁⠀⠉⠉⠑⠄⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⢀⢁⢄⠅⢄⢅⢄⢁⢀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢙⠅⠅⠀⠁⠀⠁⠀⢹⣿⣷⣄⢁⣽⣿⠗⠁⠀⠁⠀⠁⠀⢕⠅⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢀⢁⢀⢅⢄⠅⢄⢅⢀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⢔⠍⠕⠙⠁⠁⠁⠉⠁⠑⠑⠙⠕⠕⢄⠅⢄⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠙⠅⠅⠀⠁⠀⠁⠀⠁⠙⢿⢿⢿⠿⠟⠁⠁⠀⠁⠀⠁⢅⢝⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⢀⠁⢤⠕⠕⠝⠅⠑⠁⠁⠁⠉⠁⠉⠑⠝⢕⢅⠀[0m
[38;2;0;255;65m⠁⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠑⠕⢔⢅⠀⠁⠀⠁⠀⠁⠀⠁⢕⠅⠄⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠅⠅⠀⠁⠀⠁⠀⠁⠀⢁⢤⠕⠕⠉⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠑⢵⢅⠄⠁⠀⠁⠀⠁⢹⠅⠄⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢵⠅⠀⠁⠀⠁⠀⢁⢔⠕⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠉⠥⠕⠄⠁⠀⠁⢐⠕⠄⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢽⠁⠀⠁⠀⠁⢔⠝⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠙⢕⢅⠀⠁⠀⠅⢅⢁⣄⢅⣄⢅⣤⢅⣤⢅⣤⢅⣄⢅⣄⢁⢀⢕⢝⠁⠀⢁⢔⠝⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠙⢅⠁⠀⢝⣽⢿⣽⢿⣽⢿⣽⢿⣽⢿⣽⢿⣽⢿⣽⢿⣽⢿⢅⠁⢀⠝⠅⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢅⠔⠕⠅⠉⠑⢝⠍⠙⠙⠛⠝⠟⠝⠟⢽⢟⢽⢟⢽⠟⠝⠟⠝⠟⠙⠛⠍⢙⠕⠉⠁⠑⠔⠥⢄⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠵⢅⠁⠀⠁⠀⠑⢕⠅⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠠⠝⠁⠁⠀⠁⢀⢁⠝⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠉⠑⠑⠔⠕⠵⢕⢄⢅⢄⢁⢀⢁⢀⢁⢀⢁⢀⢁⢀⢁⢀⢅⢄⢕⢵⠅⠔⠑⠑⠉⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⢁⢄⠅⢀⠁⠀⠁⠀⠁⠀⢁⢤⠁⠀⠁⠀⠁⠀⠁⠀⠁⢀⠕⢍⢥⣴⢕⢴⢅⢕⠅⠅⠁⠁⠁⠁⢁⠕⢉⣵⣔⢴⢕⢍⠑⢄⠁⠀⠁⠀⠁⠀⠁⠀⠁⢀⢅⠀⠁⠀⠁⠀⠁⠀⢁⠤⢅⠄⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠁⠙⢕⢅⠀⠁⠀⠁⠀⢙⠍⠁⠀⠁⠀⠁⠀⠁⢀⠕⠜⢑⢽⢿⢿⢝⢽⢝⢵⢅⠱⠅⠄⠅⠴⠁⢼⣿⣿⢟⢵⢽⢽⢕⠄⠕⢴⠁⠀⠁⠀⠁⠀⠁⠀⠝⠅⠁⠀⠁⠀⢁⢕⠕⠁⠁⠁⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢑⠕⠅⠀⠁⠀⠕⠅⠁⠀⠁⠀⠁⠀⠁⠐⠕⠄⢝⢽⢝⢽⢽⢽⢿⣽⢿⠅⠕⠕⠕⢄⢙⢽⢝⢽⢽⣽⢿⣽⢿⡅⢑⠜⠁⠀⠁⠀⠁⠀⠁⠀⠕⢅⠁⠀⠁⢰⠍⠅⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢅⠑⠄⠁⢀⢅⠅⠁⠀⠁⠀⠁⠀⠁⠀⠁⢅⠙⢽⢿⣽⢿⣽⢿⢽⠟⢴⠁⠀⠁⠙⠅⢽⢿⣽⢿⣽⢿⣽⢿⢅⠝⠀⠁⠀⠁⠀⠁⠀⠁⠀⢝⢕⠁⠀⢑⢅⠍⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢅⠕⢅⢔⢕⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢑⢍⠙⠽⠿⠽⠟⢉⠕⠅⠁⠀⠁⠀⠙⢄⠙⠽⠿⠽⠟⢝⢵⠍⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠙⢔⠅⠔⢑⠔⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢵⠕⠕⠍⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢑⢽⠝⠕⠑⢕⠉⠁⠁⠁⠁⠀⠁⠀⠁⠀⠉⢑⠕⠑⢙⢵⢝⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢕⠑⢤⠍⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠈⢅⠄⢅⠀⠁⠀⠁⠀⠁⠀⢁⠤⠕⠉⠁⠀⠁⢅⠅⠀⠁⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢄⠕⠀⠁⠅⠑⠔⢅⢄⠁⠀⠁⠀⠁⠀⠁⠅⢀⠔⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠅⠝⠅⠁⠀⠁⠀⠁⢽⢅⠁⠅⠀⠁⠀⠁⠙⢕⠄⠁⠀⠅⢄⠁⠀⠁⢀⠅⠄⠁⠀⠕⠕⠁⠀⠁⠀⠁⠅⠁⢤⠅⠀⠁⠀⠁⠀⢝⠅⠝⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢱⠁⢵⠅⠀⠁⠀⠁⠀⠑⢕⠑⢄⠁⠀⠁⠀⠉⠑⠕⠄⢕⢄⠁⠁⠁⠁⢁⠅⠕⠕⠝⠁⠁⠀⠁⢁⠅⢔⠵⠍⠁⠀⠁⠀⠁⢴⠕⢰⠅⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢕⠅⢕⠄⠁⠀⠁⠀⠁⠀⠉⢕⠅⢅⠁⠀⠁⠀⢙⣕⢗⢑⢑⠁⢁⢕⢑⢔⢟⠅⠁⠄⠁⢀⠁⢕⢝⢁⠁⠀⠁⠀⠁⠀⢑⢕⢁⠅⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠙⢅⠑⢵⢅⢤⠕⠕⠉⠁⢑⠅⢕⠔⠅⢄⢁⠀⠉⢽⢕⢥⠽⣷⢿⢅⢕⠵⢝⠀⢁⢀⠅⠥⠕⠅⢕⠁⠉⠑⠕⢴⢅⢤⠝⠅⠜⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠑⠅⠅⠅⢁⢁⢄⠅⠄⠕⢅⢙⠀⠁⢠⠝⠁⠁⢙⠵⠕⢕⢵⠕⢔⢕⢝⠁⠀⠉⠥⠅⠀⢑⠅⠅⠅⠅⠄⢁⢁⠁⠅⠁⢴⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢁⢔⠕⠄⠝⠅⠅⠅⠕⢑⠍⢕⠕⠔⠕⢥⠝⠁⠁⠀⠁⢝⢝⢵⠗⣽⢇⢵⠝⣭⠓⠀⠁⠀⠉⠥⠝⢔⠕⢕⠍⢅⠑⠄⠅⠥⠍⠅⢕⢔⢅⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢙⠄⢅⢅⢁⢀⢁⢄⠅⠔⠅⠕⠁⠀⠑⠕⠅⠀⠁⠀⠁⠅⢷⣿⢗⣿⣿⢽⢿⣽⠅⠀⠁⠀⠁⠴⢁⠅⠁⠐⠅⠕⠕⢄⢅⢄⢁⢀⢙⠅⢕⠅⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠑⢅⠑⠅⠁⠁⠁⠀⠁⠀⠁⠀⠁⢀⠁⠵⠝⢄⠁⠀⠁⢅⢙⢿⢽⣿⣿⣽⢟⢅⠅⠀⠁⠀⠕⢁⠅⢄⢁⠀⠁⠀⠁⠀⠁⠀⠁⠁⠝⢁⠝⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢑⠅⠕⠅⠀⠁⠀⠁⢴⠝⠕⢍⢅⢅⢄⠕⠄⠅⠄⠁⠐⠝⣿⢿⣽⢽⣷⠟⢄⠁⠀⢁⠔⠑⠥⢅⢄⢅⢝⠙⢕⠅⠀⠁⠀⠁⢰⠁⢔⠅⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠑⠅⢕⠀⠁⠀⠁⠀⠑⢅⠑⢅⠁⠀⠁⠁⢅⠑⢅⠀⢕⢹⢿⣿⣿⣿⢅⠅⠁⠔⢁⠔⠁⠀⠁⢀⠕⢅⠕⠁⠁⠀⠁⠀⢁⠅⠕⠅⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢕⠝⠅⠁⠀⠁⠀⠁⠀⠑⢄⠑⢄⠁⠀⠁⠑⢅⠑⢝⠅⠽⢿⠿⠟⢝⠔⢉⠔⠁⠀⠁⠀⠕⢅⠕⠁⠁⠀⠁⠀⠁⠀⠝⢔⠅⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢕⢕⠁⠀⠁⠀⠁⠀⠁⠀⠑⢥⢕⠀⠁⠀⠁⠁⠑⠑⠁⠀⠁⠀⠑⠁⠁⠀⠁⠄⢁⠅⠕⠁⠁⠀⠁⠀⠁⠀⠁⢰⢅⠅⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠑⠅⢅⠀⠁⠀⠁⠀⠁⠀⢁⢅⠅⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠉⢕⢕⠀⠁⠀⠁⠀⠁⠀⢁⠅⢝⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⢑⢕⠕⢕⢅⠀⠁⢀⠅⢄⠜⢕⢅⢄⠅⢄⠅⢄⠅⢄⠅⢄⠅⢄⠅⢄⠅⢄⠅⢄⠅⢄⢝⢄⠅⢄⠁⠀⢁⢔⠕⢑⠙⠄⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢀⢅⠄⠁⠀⠁⠀⢁⢅⢽⠝⠁⢽⠝⢴⠝⢴⠝⢵⠝⢥⠝⢡⢽⢡⢽⢅⢽⠕⢽⠕⢽⠝⢵⢽⢽⢥⠑⠄⠁⠁⠁⠀⢅⢅⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢔⠝⠀⠁⠀⠁⢴⢁⣝⢟⣅⢙⣝⢕⢙⢅⠝⢗⣝⠛⣔⢟⢕⢟⣕⢛⣅⠝⢅⢝⠕⢝⣅⢙⣕⠔⢽⢷⠕⠅⠀⠁⠀⠁⢕⠅⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠙⠁⠀⠁⠀⠕⢡⠷⢵⠽⢵⠔⢵⢵⠵⠹⢵⠝⢱⠵⠵⠱⢴⠝⢵⠼⠅⢵⢵⠍⢵⠽⠕⠵⢵⠅⢴⠵⢵⠝⢄⠁⠀⠁⠙⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢔⢑⢝⢟⢁⢟⢝⢑⢝⢟⢅⢝⢝⢟⢽⢟⢝⢟⢽⢟⢝⢟⢕⢘⢝⢗⢐⢟⢅⢝⢕⢙⢕⢅⢵⢗⢄⢅⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⢵⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⢁⠅⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
[38;2;0;255;65m⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀⠁⠀[0m
                                          
{PROMPT} [root@{title.lower()[:18]}]# {RST}
"""

NOTICE = (
    f"{Fore.RED}"
    "[𓆧] GrasshoppeR | M1AT§UN0."
    f"{Style.RESET_ALL}"
)

MAIN_MENU = """
[1] Rede
[2] Arquivos
[3] Cricket-Term
[4] MoonScan
[5] Rasco
[6] Mianba
[7] JesterCopyCat

[?] Ajuda                 [0] Sair"""

NETWORK_MENU = """[1] Consulta DNS
[2] Cabeçalhos HTTP
[3] Certificado TLS
[4] Verificar portas TCP
[0] Voltar"""

FILE_MENU = """[1] SHA-256 de arquivo
[2] Metadados de arquivo
[3] Criar manifest
[4] Comparar manifest
[5] Inspecionar Zipes (.zip)
[0] Voltar"""

PROGRAMS = {
    "4": {"name": "MoonScan", "stems": ("moonscan",)},
    "5": {"name": "Rasco", "stems": ("RascoOsint",)},
    "6": {"name": "Mianba", "stems": ("Mianba",)},
    "7": {"name": "JesterCopyCat", "stems": ("jester",)},
}

SUPPORTED_RUNTIMES = {
    ".sh": ("bash", "sh"),
    ".bash": ("bash",),
    ".command": ("bash", "sh"),
    ".zsh": ("zsh",),
    ".fish": ("fish",),
    ".js": ("node",),
    ".mjs": ("node",),
    ".cjs": ("node",),
    ".rb": ("ruby",),
    ".pl": ("perl",),
    ".php": ("php",),
    ".lua": ("lua",),
    ".r": ("Rscript",),
    ".swift": ("swift",),
    ".go": ("go",),
    ".ps1": ("pwsh", "powershell"),
    ".bat": ("cmd",),
    ".cmd": ("cmd",),
    ".jar": ("java",),
    ".vbs": ("cscript",),
}

NATIVE_EXTENSIONS = {".exe", ".com", ".bin", ".out"}
IGNORED_DIRECTORIES = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".mypy_cache", ".pytest_cache",
}
HISTORY_LIMIT = 100
EXTERNAL_TERMINATE_TIMEOUT = 3
EXTERNAL_HISTORY = []

INSTALL_FRAMES = [
    ("Grasshopper...", "—"),
    ("Grasshopper..", "\\"),
    ("Grasshopper.", "l"),
    ("Grasshopper...", "/"),
    ("Grasshopper..", "—"),
    ("Grasshopper.", "◇"),
    ("Grasshopper...", "□"),
    ("Grasshopper..", "◇"),
    ("Grasshopper...", "—"),
    ("Grasshopper...", "\\"),
    ("Grasshopper...", "l"),
    ("Grasshopper...", "/"),
    ("Grasshopper...", "—"),
    ("Grasshopper...", "◇"),
    ("Grasshopper...", "□"),
    ("Grasshopper...", "◇"),
    ("Grasshopper...", "—"),
    ("Grasshopper..", "\\"),
    ("Grasshopper.", "l"),
    ("Grasshopper...", "/"),
    ("Grasshopper..", "—"),
    ("Grasshopper.", "◇"),
    ("Grasshopper...", "□"),
    ("Grasshopper..", "◇"),
    ("Grasshopper...", "—"),
    ("Grasshopper...", "\\"),
    ("Grasshopper...", "l"),
    ("Grasshopper...", "/"),
    ("Grasshopper...", "—"),
    ("Grasshopper...", "◇"),
    ("Grasshopper...", "□"),
    ("Grasshopper...", "◇"),
]


def error(message):
    print(f"{Fore.RED}Erro: {message}{Style.RESET_ALL}")


def success(message):
    print(f"{Fore.GREEN}[+] {message}{Style.RESET_ALL}")


def info(message):
    print(f"{Fore.CYAN}[*] {message}{Style.RESET_ALL}")


def ask(label):
    value = input(f"{Fore.CYAN}{label}{Style.RESET_ALL}").strip()
    if not value:
        raise ValueError("O campo não pode ficar vazio.")
    return value


def ask_path(label):
    return Path(os.path.expanduser(ask(label)))


def parse_ports(value):
    try:
        ports = [int(part.strip()) for part in value.split(",")]
    except ValueError as exc:
        raise ValueError(
            "As portas precisam ser separadas por vírgula."
        ) from exc

    if not ports or len(ports) > 32:
        raise ValueError("Informe de 1 a 32 portas.")

    if any(port < 1 or port > 65535 for port in ports):
        raise ValueError("As portas devem estar entre 1 e 65535.")

    return ports


def display_result(result):
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    destination = input(
        "Salvar JSON em arquivo? Caminho ou Enter para não salvar: "
    ).strip()

    if destination:
        path = Path(os.path.expanduser(destination))
        with path.open("x", encoding="utf-8") as stream:
            stream.write(output + "\n")
        success(f"JSON salvo em: {path}")


def load_manifest(label):
    path = ask_path(label)
    with path.open("r", encoding="utf-8") as stream:
        result = json.load(stream)

    if not isinstance(result, dict):
        raise ValueError(f"O manifesto {path} deve ser um JSON.")

    return result


def iter_tool_files():
    for current, directories, filenames in os.walk(TOOLS_DIR):
        directories[:] = sorted(
            directory for directory in directories
            if directory not in IGNORED_DIRECTORIES
            and not directory.startswith(".")
        )

        for filename in filenames:
            path = Path(current) / filename
            if path.is_file() and not path.is_symlink():
                yield path


def find_program_file(stems):
    if isinstance(stems, str):
        stems = (stems,)

    accepted = {stem.casefold() for stem in stems}
    matches = [
        path for path in iter_tool_files()
        if path.stem.casefold() in accepted
    ]

    if not matches:
        expected = " ou ".join(stems)
        raise FileNotFoundError(
            f"Nenhum arquivo pra {expected} foi encontrado na {TOOLS_DIR}."
        )

    if len(matches) > 1:
        names = ", ".join(
            str(path.relative_to(TOOLS_DIR))
            for path in sorted(matches)
        )
        raise RuntimeError(
            f"Mais de um arquivo corresponde à ferramenta: {names}. "
            "Mantenha apenas uma versão ativa."
        )

    return matches[0].resolve(strict=True)


def find_runtime(extension):
    candidates = SUPPORTED_RUNTIMES.get(extension.lower())

    if candidates:
        for candidate in candidates:
            executable = shutil.which(candidate)
            if executable:
                return executable

        raise RuntimeError(
            f"Interpretador não encontrado para {extension}. "
            f"É necessário instalar: {' ou '.join(candidates)}."
        )

    if extension.lower() in NATIVE_EXTENSIONS:
        return None

    raise ValueError(
        f"Formato não suportado: {extension or 'arquivo sem extensão'}."
    )


def build_execution_command(path):
    path = Path(path).resolve(strict=True)
    extension = path.suffix.lower()

    if extension in (".py", ".pyw"):
        return [sys.executable, "-u", str(path)]

    if extension in (".sh", ".bash", ".command", ".zsh", ".fish"):
        return [find_runtime(extension), str(path)]

    if extension == ".go":
        return [find_runtime(extension), "run", str(path)]
 
    if extension in (
        ".js", ".mjs", ".cjs", ".rb", ".pl", ".php", ".lua",
        ".r", ".swift",
    ):
        return [find_runtime(extension), str(path)]

    if extension == ".ps1":
        return [
            find_runtime(extension),
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(path),
        ]

    if extension in (".bat", ".cmd"):
        if os.name != "nt":
            raise RuntimeError("Arquivos BAT e CMD só podem ser executados no Windows.")
        return [find_runtime(extension), "/d", "/c", str(path)]

    if extension == ".vbs":
        if os.name != "nt":
            raise RuntimeError("Arquivos VBS só podem ser executados no Windows.")
        return [find_runtime(extension), "//Nologo", str(path)]

    if extension == ".jar":
        return [find_runtime(extension), "-jar", str(path)]

    if extension in NATIVE_EXTENSIONS or (
        not extension and os.name != "nt" and os.access(path, os.X_OK)
    ):
        if os.name != "nt" and not os.access(path, os.X_OK):
            raise PermissionError(
                "O arquivo não possui permissão de execução."
            )
        return [str(path)]

    raise ValueError(
        f"Formato não suportado: {extension or 'arquivo sem extensão'}."
    )


def validate_program(path):
    if path.suffix.lower() in (".py", ".pyw"):
        with path.open("rb") as stream:
            compile(stream.read(), str(path), "exec")


def terminate_external_process(process):
    if process is None or process.poll() is not None:
        return

    try:
        process.terminate()
    except ProcessLookupError:
        return
    except OSError as exc:
        if process.poll() is not None:
            return
        try:
            process.kill()
        except (ProcessLookupError, OSError):
            error(f"Não foi possível encerrar o processo: {exc}")
            return

    try:
        process.wait(timeout=EXTERNAL_TERMINATE_TIMEOUT)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except (ProcessLookupError, OSError):
            pass
        try:
            process.wait()
        except OSError as exc:
            error(f"Falha ao aguardar o encerramento: {exc}")
    except (ProcessLookupError, OSError):
        pass


def show_install_animation(process):
    index = 0

    while process.poll() is None:
        label, symbol = INSTALL_FRAMES[index % len(INSTALL_FRAMES)]
        print(
            f"\r{Fore.GREEN}{label}   {symbol}{Style.RESET_ALL}",
            end="",
            flush=True,
        )
        index += 1
        time.sleep(0.12)

    print("\r" + " " * 48 + "\r", end="", flush=True)


def run_installer(command, working_directory, description):
    process = None

    with tempfile.TemporaryFile(mode="w+b") as error_log:
        try:
            process = subprocess.Popen(
                command,
                cwd=str(working_directory),
                stdin=None,
                stdout=subprocess.DEVNULL,
                stderr=error_log,
                shell=False,
            )

            try:
                show_install_animation(process)
                returncode = process.wait()
            except KeyboardInterrupt:
                terminate_external_process(process)
                raise

            if returncode != 0:
                error_log.seek(0)
                details = error_log.read().decode("utf-8", errors="replace").strip()
                error(f"Falha ao instalar {description}. Código: {returncode}.")
                if details:
                    print(details[-8000:])
                return False

            success(f"{description} instalado.")
            return True

        except OSError as exc:
            error(f"Não foi possível iniciar o instalador: {exc}")
            return False
        finally:
            if process is not None and process.poll() is None:
                terminate_external_process(process)


def install_requirements(requirements_file):
    requirements_file = requirements_file.resolve()

    if not requirements_file.is_file():
        return True

    answer = input(
        f"Dependências Python declaradas em "
        f"{requirements_file.relative_to(BASE_DIR) if requirements_file.is_relative_to(BASE_DIR) else requirements_file}. "
        "Instalar agora? [s/N]: "
    ).strip().lower()

    if answer not in ("s", "sim"):
        info("Instalação Python ignorada.")
        return False

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "-r",
        str(requirements_file),
    ]

    return run_installer(command, requirements_file.parent, "dependências Python")


def install_project_dependencies(program_path):
    candidates = []
    shared_requirements = TOOLS_DIR / "requirements.txt"
    local_requirements = program_path.parent / "requirements.txt"

    if shared_requirements.is_file():
        candidates.append(shared_requirements)

    if local_requirements.is_file() and local_requirements.resolve() != shared_requirements.resolve():
        candidates.append(local_requirements)

    for requirements_file in candidates:
        if not install_requirements(requirements_file):
            return False

    package_json = program_path.parent / "package.json"
    node_modules = program_path.parent / "node_modules"

    if package_json.is_file() and not node_modules.is_dir():
        npm = shutil.which("npm")

        if npm is None:
            error("package.json encontrado, mas Node.js/npm não está instalado.")
            return False

        answer = input(
            "Dependências Node.js encontradas. Instalar com npm? [s/N]: "
        ).strip().lower()

        if answer not in ("s", "sim"):
            info("Instalação Node.js ignorada.")
            return False

        if not run_installer(
            [npm, "install", "--no-audit", "--no-fund"],
            program_path.parent,
            "dependências Node.js",
        ):
            return False

    return True


def register_history(entry):
    EXTERNAL_HISTORY.append(entry)

    if len(EXTERNAL_HISTORY) > HISTORY_LIMIT:
        del EXTERNAL_HISTORY[:-HISTORY_LIMIT]


def launch_program(program_id):
    config = PROGRAMS.get(str(program_id))

    if config is None:
        error("Programa não cadastrado.")
        return

    name = config["name"]
    process = None
    started_at = time.monotonic()
    program_path = None
    returncode = None
    interrupted = False

    print()

    try:
        program_path = find_program_file(config["stems"])
        command = build_execution_command(program_path)
        validate_program(program_path)

        info(f"Ferramenta: {name}")
        info(f"Arquivo: {program_path.relative_to(TOOLS_DIR)}")
        info(f"Formato: {program_path.suffix or 'executável nativo'}")
        info("O programa será executado com os privilégios da sua conta.")

        answer = input(f"Executar {name}? [s/N]: ").strip().lower()
        if answer not in ("s", "sim"):
            print("Execução cancelada.")
            return

        if not install_project_dependencies(program_path):
            info("A ferramenta não foi iniciada.")
            return

        print(
            f"\n{Fore.GREEN}[+] Abrindo {name}. "
            f"A interface original será mantida.{Style.RESET_ALL}\n",
            flush=True,
        )

        process = subprocess.Popen(
            command,
            cwd=str(program_path.parent),
            stdin=None,
            stdout=None,
            stderr=None,
            shell=False,
        )

        info(f"Processo iniciado. PID: {process.pid}")

        try:
            returncode = process.wait()
        except KeyboardInterrupt:
            interrupted = True
            print("\nInterrupção recebida. Encerrando a ferramenta...")
            terminate_external_process(process)
            returncode = process.poll()

        elapsed = round(time.monotonic() - started_at, 3)

        if interrupted:
            info(f"{name} foi interrompido.")
        elif returncode == 0:
            success(f"{name} foi encerrado normalmente.")
        else:
            error(f"{name} terminou com código {returncode}.")

        register_history({
            "name": name,
            "file": str(program_path),
            "pid": process.pid,
            "returncode": returncode,
            "duration_seconds": elapsed,
            "interrupted": interrupted,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    except SyntaxError as exc:
        error(f"Erro de sintaxe na linha {exc.lineno}: {exc.msg}")
    except (OSError, ValueError, RuntimeError) as exc:
        error(exc)
    except EOFError:
        raise
    except KeyboardInterrupt:
        interrupted = True
        terminate_external_process(process)
        print("\nInicialização interrompida.")
    except Exception as exc:
        error(f"Falha inesperada ao iniciar {name}: {exc}")
    finally:
        if process is not None and process.poll() is None:
            terminate_external_process(process)

        print(
            f"\n{Fore.GREEN}[+] Controle devolvido à {title} Suite.{Style.RESET_ALL}\n",
            flush=True,
        )


def external_history_menu():
    if not EXTERNAL_HISTORY:
        info("Ainda não há ferramentas executadas nesta sessão.")
        return

    print("\nHistórico desta sessão")
    for index, item in enumerate(EXTERNAL_HISTORY, 1):
        if item["interrupted"]:
            status = "interrompido"
        elif item["returncode"] == 0:
            status = "concluído"
        else:
            status = f"código {item['returncode']}"

        print(
            f"[{index}] {item['name']} | {item['timestamp']} | "
            f"{status} | {item['duration_seconds']}s"
        )


def tool_status():
    print("\nEstado das ferramentas")
    for key, config in PROGRAMS.items():
        try:
            path = find_program_file(config["stems"])
            state = f"encontrada: {path.relative_to(TOOLS_DIR)}"
        except FileNotFoundError:
            state = "aguardando arquivo em tools/"
        except RuntimeError as exc:
            state = str(exc)

        print(f"[{key}] {config['name']}: {state}")


def network_menu():
    if net is None:
        error(f"Módulo network_tools indisponível: {NETWORK_IMPORT_ERROR}")
        return

    print(NOTICE)

    while True:
        print(f"{Fore.WHITE}{NETWORK_MENU}{Style.RESET_ALL}")

        try:
            choice = input("Rede> ").strip()

            if choice == "0":
                return
            if choice == "1":
                result = net.dns_lookup(ask("Host: "))
            elif choice == "2":
                result = net.http_headers(ask("URL: "))
            elif choice == "3":
                host = ask("Host: ")
                port_text = input("Porta TLS [443]: ").strip()

                if port_text and "," in port_text:
                    raise ValueError("Informe apenas uma porta TLS.")

                port = parse_ports(port_text)[0] if port_text else 443
                result = net.tls_certificate(host, port)
            elif choice == "4":
                host = ask("Host: ")
                ports = parse_ports(ask("Portas separadas por vírgulas: "))
                answer = input(
                    "Você tem autorização para testar esse host? [s/N]: "
                ).strip().lower()

                if answer not in ("s", "sim"):
                    print("Teste cancelado.")
                    continue

                result = net.tcp_ports(host, ports, authorized=True)
            else:
                error("Opção inválida. Escolha um número do menu.")
                continue

            display_result(result)

        except EOFError:
            raise
        except KeyboardInterrupt:
            print("\nOperação interrompida. Voltando ao menu de rede.")
        except Exception as exc:
            error(exc)


def file_menu():
    if ft is None:
        error(f"Módulo file_tools indisponível: {FILE_IMPORT_ERROR}")
        return

    while True:
        print(f"{Fore.WHITE}{FILE_MENU}{Style.RESET_ALL}")

        try:
            choice = input("Arquivos> ").strip()

            if choice == "0":
                return
            if choice == "1":
                result = ft.sha256_file(ask_path("Caminho do arquivo: "))
            elif choice == "2":
                result = ft.file_metadata(ask_path("Caminho do arquivo: "))
            elif choice == "3":
                result = ft.directory_manifest(ask_path("Diretório: "))
            elif choice == "4":
                old = load_manifest("Manifesto anterior (JSON): ")
                new = load_manifest("Manifesto atual (JSON): ")
                result = ft.compare_manifests(old, new)
            elif choice == "5":
                result = ft.inspect_zip(ask_path("Caminho do ZIP: "))
            else:
                error("Opção inválida. Escolha um número do menu.")
                continue

            display_result(result)

        except EOFError:
            raise
        except KeyboardInterrupt:
            print("\nOperação interrompida. Voltando ao menu de arquivos.")
        except Exception as exc:
            error(exc)


def run_command(command):
    command = command.strip()

    if not command:
        return

    if command == "cd" or command.startswith(("cd ", "cd\t")):
        parts = shlex.split(command, posix=(os.name != "nt"))

        if len(parts) > 2:
            raise ValueError("Uso: cd [diretório]")

        destination = parts[1] if len(parts) == 2 else "~"
        os.chdir(os.path.expanduser(destination))
        return

    result = subprocess.run(command, shell=True, check=False)

    if result.returncode:
        error(f"Comando terminou com código {result.returncode}.")


def command_mode():
    print(Fore.GREEN + "Use 'voltar' ou 'exit' para retornar ao GrasshoppeR.")

    while True:
        try:
            command = input(
    f"{Fore.CYAN}╚═══"
    f"{Fore.GREEN}C"
    f"{Fore.CYAN}R"
    f"{Fore.BLUE}I"
    f"{Fore.CYAN}C"
    f"{Fore.GREEN}K"
    f"{Fore.CYAN}E"
    f"{Fore.BLUE}T:~  $"
    f"{Style.RESET_ALL}  "
).strip()

            if command in ("voltar", "exit"):
                return

            run_command(command)

        except (OSError, ValueError, RuntimeError) as exc:
            error(exc)
        except EOFError:
            raise
        except KeyboardInterrupt:
            print("\nInterrompido. Voltando ao menu principal.")
            return


def help_menu():
    print("\nGrasshoppeR Suite — M1AT§UN0")
    time.sleep(2)
    print("Os arquivos das ferramentas ficam na pasta tools/ ou em subpastas dela.")
    time.sleep(2)
    print("""Para usar ferramentas de pentest use os seguintes comandos em ordem:
        
         • 3 (apenas o número 3, dê enter, e entrará no modo Cricket-Terminal)
         Já dentro de Cricket-Term, use:
         • python3 pentest_tools.py --help
         """)
    print("""Formatos reconhecidos: Python, Shell, JavaScript, Ruby, Perl, PHP, Lua, R, Swift, Go, PowerShell, BAT, CMD, VBS, JAR e executáveis nativos. O Cricket-Terminal permite clonagem de repositórios de arquivos para o diretório "Suíte" via git clone.""")
    print("Dependências Python: requirements.txt na pasta tools/ ou junto da ferramenta.")
    time.sleep(1)
    print("Dependências Bash: install.sh")
    print("A instalação de dependências sempre pede confirmação quando direta do GrasshoppeR.")
    time.sleep(2)
    print("Interpretadores ausentes precisam ser instalados pelo usuário.")
    time.sleep(1)
    print("As ferramentas externas não são isoladas.")
    time.sleep(2)
    print("Lembre-se, você pode baixar qualquer ferramenta apartir de qualquer repositório do GitHub usando git clone dentro da GrasshoppeR Suite diretamente do Cricket Terminal, sem precisar encerrar o programa.")
    print(NOTICE)
    tool_status()
    external_history_menu()


def main():
    print(f"{Fore.GREEN}{Style.BRIGHT}{BANNER}{Style.RESET_ALL}")
    print(NOTICE)
    print(f"Pasta de ferramentas: {TOOLS_DIR}\n")

    while True:
        try:
            print(f"{Fore.WHITE}{MAIN_MENU}{Style.RESET_ALL}")
            choice = input(
                f"{Fore.GREEN}#GrasshoppeR/𓆧>    {Style.RESET_ALL}"
            ).strip()

            if choice == "0":
                print("Até mais.")
                return 0
            if choice == "1":
                network_menu()
            elif choice == "2":
                file_menu()
            elif choice == "3":
                command_mode()
            elif choice in PROGRAMS:
                launch_program(choice)
            elif choice == "?":
                help_menu()
            else:
                error("Não tem essa opção.")

        except EOFError:
            print("\nAté mais.")
            return 0
        except KeyboardInterrupt:
            print("\nInterrompido. Voltando ao menu principal.")
        except Exception as exc:
            error(exc)


if __name__ == "__main__":
    sys.exit(main())
