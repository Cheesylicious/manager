import ctypes
import time
from ctypes import wintypes

# ------------------------------------------------------------------
# Low-Level Input (ScanCodes) - German Layout Support (Fixed)
# ------------------------------------------------------------------

# Strukturen
PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_short)]


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]


class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]


user32 = ctypes.windll.user32

# Konstanten
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

# --- ScanCodes (Deutsch) ---
# WICHTIG: Der Name muss SCANCODES sein, damit der Manager ihn findet!
SCANCODES = {
    'esc': 0x01, '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06, '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A,
    '0': 0x0B, 'ß': 0x0C,
    'backspace': 0x0E, 'tab': 0x0F, 'enter': 0x1C, 'ctrl': 0x1D, 'shift': 0x2A, 'alt': 0x38, 'space': 0x39,
    'q': 0x10, 'w': 0x11, 'e': 0x12, 'r': 0x13, 't': 0x14, 'z': 0x15, 'u': 0x16, 'i': 0x17, 'o': 0x18, 'p': 0x19,
    'ü': 0x1A, '+': 0x1B,
    'a': 0x1E, 's': 0x1F, 'd': 0x20, 'f': 0x21, 'g': 0x22, 'h': 0x23, 'j': 0x24, 'k': 0x25, 'l': 0x26, 'ö': 0x27,
    'ä': 0x28, '#': 0x2B,
    '<': 0x56, 'y': 0x2C, 'x': 0x2D, 'c': 0x2E, 'v': 0x2F, 'b': 0x30, 'n': 0x31, 'm': 0x32, ',': 0x33, '.': 0x34,
    '-': 0x35,
    '^': 0x29
}

# Mapping: 'Zeichen': (Basis_ScanCode, Braucht_Shift, Braucht_AltGr)
CHAR_MAP = {}

# 1. Kleinbuchstaben & Zahlen füllen
for char, code in SCANCODES.items():
    if len(char) == 1:
        CHAR_MAP[char] = (code, False, False)

# 2. Großbuchstaben
upper_map = {
    'Q': 'q', 'W': 'w', 'E': 'e', 'R': 'r', 'T': 't', 'Z': 'z', 'U': 'u', 'I': 'i', 'O': 'o', 'P': 'p', 'Ü': 'ü',
    'A': 'a', 'S': 's', 'D': 'd', 'F': 'f', 'G': 'g', 'H': 'h', 'J': 'j', 'K': 'k', 'L': 'l', 'Ö': 'ö', 'Ä': 'ä',
    'Y': 'y', 'X': 'x', 'C': 'c', 'V': 'v', 'B': 'b', 'N': 'n', 'M': 'm'
}
for upper, lower in upper_map.items():
    CHAR_MAP[upper] = (SCANCODES[lower], True, False)

# 3. Sonderzeichen (DE Layout)
SPECIALS = {
    '!': ('1', True, False),
    '"': ('2', True, False),
    '§': ('3', True, False),
    '$': ('4', True, False),
    '%': ('5', True, False),
    '&': ('6', True, False),
    '/': ('7', True, False),
    '(': ('8', True, False),
    ')': ('9', True, False),
    '=': ('0', True, False),
    '?': ('ß', True, False),
    '`': ('´', False, True),
    '*': ('+', True, False),
    "'": ('#', True, False),
    ';': (',', True, False),
    ':': ('.', True, False),
    '_': ('-', True, False),
    '>': ('<', True, False),
    '|': ('<', False, True),
    '@': ('q', False, True),  # AltGr + q
    '€': ('e', False, True),
    '{': ('7', False, True),
    '[': ('8', False, True),
    ']': ('9', False, True),
    '}': ('0', False, True),
    '\\': ('ß', False, True),
    '~': ('+', False, True)
}

for char, (base_key_name, shift, altgr) in SPECIALS.items():
    if base_key_name in SCANCODES:
        CHAR_MAP[char] = (SCANCODES[base_key_name], shift, altgr)


def press_key(scancode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scancode, KEYEVENTF_SCANCODE, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def release_key(scancode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scancode, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def click_key(scancode):
    press_key(scancode)
    time.sleep(0.02)
    release_key(scancode)


def type_string(text):
    """Tippt Text inkl. deutscher Sonderzeichen"""
    for char in text:
        if char in CHAR_MAP:
            scancode, need_shift, need_altgr = CHAR_MAP[char]

            if need_altgr:
                press_key(SCANCODES['ctrl'])
                press_key(SCANCODES['alt'])
            elif need_shift:
                press_key(SCANCODES['shift'])

            click_key(scancode)

            if need_altgr:
                release_key(SCANCODES['alt'])
                release_key(SCANCODES['ctrl'])
            elif need_shift:
                release_key(SCANCODES['shift'])
        else:
            print(f"Zeichen '{char}' unbekannt.")

        time.sleep(0.05)


# --- Maus ---
def mouse_move_abs(x, y):
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    norm_x = int(x * 65535 / screen_w)
    norm_y = int(y * 65535 / screen_h)
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.mi = MouseInput(norm_x, norm_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, ctypes.pointer(extra))
    inp = Input(ctypes.c_ulong(0), ii_)
    user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))


def mouse_click():
    extra = ctypes.c_ulong(0)
    ii_ = Input_I();
    ii_.mi = MouseInput(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, ctypes.pointer(extra))
    user32.SendInput(1, ctypes.pointer(Input(ctypes.c_ulong(0), ii_)), ctypes.sizeof(Input))
    time.sleep(0.05)
    ii_.mi = MouseInput(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, ctypes.pointer(extra))
    user32.SendInput(1, ctypes.pointer(Input(ctypes.c_ulong(0), ii_)), ctypes.sizeof(Input))


def click_at(x, y):
    mouse_move_abs(x, y)
    time.sleep(0.1)
    mouse_click()