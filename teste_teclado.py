import ctypes
from ctypes import wintypes
import time
import keyboard

user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.LPVOID),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.LPVOID),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)

    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


user32.SendInput.argtypes = [
    wintypes.UINT,
    ctypes.POINTER(INPUT),
    ctypes.c_int,
]

user32.SendInput.restype = wintypes.UINT


def send_key(vk, key_up=False):

    flags = KEYEVENTF_KEYUP if key_up else 0

    inp = INPUT()

    inp.type = INPUT_KEYBOARD

    inp.ki = KEYBDINPUT(
        wVk=vk,
        wScan=0,
        dwFlags=flags,
        time=0,
        dwExtraInfo=None,
    )

    result = user32.SendInput(
        1,
        ctypes.byref(inp),
        ctypes.sizeof(INPUT)
    )

    error = ctypes.get_last_error()

    print(
        f"VK=0x{vk:02X} "
        f"{'UP' if key_up else 'DOWN'} "
        f"-> SendInput={result}, "
        f"LastError={error}"
    )

    if result == 0:
        print(
            "ERRO:",
            ctypes.WinError(error)
        )

    return result


def press(vk):

    send_key(vk, False)

    time.sleep(0.05)

    send_key(vk, True)

    time.sleep(0.05)


print("=" * 55)
print("TESTE DE TECLADO COM ALT+TAB")
print("=" * 55)

print()
print("Tamanho da estrutura INPUT:")
print(ctypes.sizeof(INPUT))

print()
print("Você tem 5 segundos para se preparar...")
print("Deixe o VS Code em primeiro plano.")
print()

time.sleep(5)

# ============================================================
# ALT + TAB
# ============================================================

print()
print("Enviando ALT+TAB...")

keyboard.press("alt")

time.sleep(0.1)

keyboard.press_and_release("tab")

time.sleep(0.1)

keyboard.release("alt")

print("Alt+Tab enviado.")

# Dá um tempo para a janela receber o foco
time.sleep(1)

# ============================================================
# DIGITA abc123
# ============================================================

print()
print("Digitando abc123...")

press(0x41)  # A
press(0x42)  # B
press(0x43)  # C
press(0x31)  # 1
press(0x32)  # 2
press(0x33)  # 3

# ============================================================
# ENTER
# ============================================================

print()
print("Enviando ENTER...")

press(0x0D)

print()
print("=" * 55)
print("TESTE TERMINADO")
print("=" * 55)

input("Pressione ENTER para fechar...")