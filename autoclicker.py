import tkinter as tk
from tkinter import Toplevel, messagebox
import threading
import keyboard
import time
import ctypes
from ctypes import wintypes
from pynput import mouse
import json
import os
import base64


# ============================================================
# DEBUG
# ============================================================

DEBUG = True


def debug(message):
    if DEBUG:
        print(f"[DEBUG] {message}", flush=True)


# ============================================================
# WINDOWS / DLL
# ============================================================

user32 = ctypes.WinDLL(
    "user32",
    use_last_error=True
)

crypt32 = ctypes.WinDLL(
    "crypt32",
    use_last_error=True
)

kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True
)


# ============================================================
# DPAPI - CRIPTOGRAFIA DA SENHA
# ============================================================

class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte))
    ]


crypt32.CryptProtectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    wintypes.LPCWSTR,
    ctypes.POINTER(DATA_BLOB),
    wintypes.LPVOID,
    ctypes.POINTER(DATA_BLOB),
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB)
]

crypt32.CryptProtectData.restype = wintypes.BOOL


crypt32.CryptUnprotectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    ctypes.POINTER(wintypes.LPWSTR),
    ctypes.POINTER(DATA_BLOB),
    wintypes.LPVOID,
    ctypes.POINTER(DATA_BLOB),
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB)
]

crypt32.CryptUnprotectData.restype = wintypes.BOOL


kernel32.LocalFree.argtypes = [
    wintypes.HLOCAL
]

kernel32.LocalFree.restype = wintypes.HLOCAL


def encrypt_password(password):

    if not password:
        return ""

    password_bytes = password.encode("utf-8")

    buffer = ctypes.create_string_buffer(
        password_bytes
    )

    data_in = DATA_BLOB(
        len(password_bytes),
        ctypes.cast(
            buffer,
            ctypes.POINTER(ctypes.c_byte)
        )
    )

    data_out = DATA_BLOB()

    result = crypt32.CryptProtectData(
        ctypes.byref(data_in),
        "AutoClicker Password",
        None,
        None,
        None,
        0,
        ctypes.byref(data_out)
    )

    debug(
        f"[DPAPI] CryptProtectData retornou: {result}"
    )

    if not result:
        raise ctypes.WinError(
            ctypes.get_last_error()
        )

    try:

        encrypted = ctypes.string_at(
            data_out.pbData,
            data_out.cbData
        )

        return base64.b64encode(
            encrypted
        ).decode("ascii")

    finally:

        kernel32.LocalFree(
            data_out.pbData
        )


def decrypt_password(encrypted_password):

    if not encrypted_password:
        return ""

    try:

        encrypted = base64.b64decode(
            encrypted_password
        )

        buffer = ctypes.create_string_buffer(
            encrypted
        )

        data_in = DATA_BLOB(
            len(encrypted),
            ctypes.cast(
                buffer,
                ctypes.POINTER(ctypes.c_byte)
            )
        )

        data_out = DATA_BLOB()

        description = wintypes.LPWSTR()

        result = crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            ctypes.byref(description),
            None,
            None,
            None,
            0,
            ctypes.byref(data_out)
        )

        debug(
            f"[DPAPI] CryptUnprotectData retornou: {result}"
        )

        if not result:
            debug(
                "[DPAPI] Não foi possível "
                "descriptografar a senha."
            )
            return ""

        try:

            decrypted = ctypes.string_at(
                data_out.pbData,
                data_out.cbData
            )

            return decrypted.decode("utf-8")

        finally:

            kernel32.LocalFree(
                data_out.pbData
            )

    except Exception as e:

        debug(
            f"[DPAPI] Erro ao descriptografar: {e}"
        )

        return ""


# ============================================================
# TECLADO - SENDINPUT
# ============================================================

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
    ctypes.c_int
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
        dwExtraInfo=None
    )

    result = user32.SendInput(
        1,
        ctypes.byref(inp),
        ctypes.sizeof(INPUT)
    )

    if result == 0:

        error = ctypes.get_last_error()

        debug(
            f"[KEYBOARD] SendInput ERRO: "
            f"VK=0x{vk:02X}, "
            f"LastError={error}"
        )

        return False

    return True


def press_key(vk):

    down = send_key(
        vk,
        False
    )

    time.sleep(0.01)

    up = send_key(
        vk,
        True
    )

    return down, up


def press_shift():

    return send_key(
        0x10,
        False
    )


def release_shift():

    return send_key(
        0x10,
        True
    )


# ============================================================
# MAPA DO TECLADO
# ============================================================

KEY_MAP = {

    "a": 0x41,
    "b": 0x42,
    "c": 0x43,
    "d": 0x44,
    "e": 0x45,
    "f": 0x46,
    "g": 0x47,
    "h": 0x48,
    "i": 0x49,
    "j": 0x4A,
    "k": 0x4B,
    "l": 0x4C,
    "m": 0x4D,
    "n": 0x4E,
    "o": 0x4F,
    "p": 0x50,
    "q": 0x51,
    "r": 0x52,
    "s": 0x53,
    "t": 0x54,
    "u": 0x55,
    "v": 0x56,
    "w": 0x57,
    "x": 0x58,
    "y": 0x59,
    "z": 0x5A,

    "0": 0x30,
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
    "7": 0x37,
    "8": 0x38,
    "9": 0x39,

    " ": 0x20,

    "-": 0xBD,
    "=": 0xBB,

    "[": 0xDB,
    "]": 0xDD,
    "\\": 0xDC,

    ";": 0xBA,
    "'": 0xDE,

    ",": 0xBC,
    ".": 0xBE,
    "/": 0xBF,

    "`": 0xC0
}


SHIFT_MAP = {

    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",

    "_": "-",
    "+": "=",

    "{": "[",
    "}": "]",
    "|": "\\",

    ":": ";",
    '"': "'",

    "<": ",",
    ">": ".",
    "?": "/",

    "~": "`"
}


# ============================================================
# TIMER
# ============================================================

class TimerController:

    def __init__(self, label, root):

        self.label = label
        self.root = root

        self._stop_event = threading.Event()
        self.thread = None

    def start(self, duration_sec):

        self.stop()

        self._stop_event.clear()

        self.thread = threading.Thread(
            target=self._run_timer,
            args=(duration_sec,),
            daemon=True
        )

        self.thread.start()

    def stop(self):

        self._stop_event.set()

        if self.thread and self.thread.is_alive():

            self.thread.join(
                timeout=0.1
            )

    def _run_timer(self, total_seconds):

        for remaining in range(
            total_seconds,
            0,
            -1
        ):

            if self._stop_event.is_set():
                break

            minutes, seconds = divmod(
                remaining,
                60
            )

            self.root.after(
                0,
                lambda m=minutes, s=seconds:
                self.label.config(
                    text=
                    f"Tempo restante: "
                    f"{m:02}:{s:02}"
                )
            )

            time.sleep(1)

        if not self._stop_event.is_set():

            self.root.after(
                0,
                lambda:
                self.label.config(
                    text=
                    "Tempo restante: 00:00"
                )
            )


# ============================================================
# AUTO CLICKER APP
# ============================================================

class AutoClickerApp:

    def __init__(self, root):

        debug("================================================")
        debug("Iniciando Auto Clicker")
        debug("================================================")

        self.root = root

        self.root.title(
            "Auto Clicker Personalizável"
        )

        self.root.geometry(
            "430x205"
        )

        self.root.resizable(
            False,
            False
        )

        # ----------------------------------------------------
        # CONFIGURAÇÃO PADRÃO
        # ----------------------------------------------------

        self.running = False

        self.target_x = -994
        self.target_y = 112

        self.minutes = 2
        self.seconds = 30

        self.enable_alt_tab = True

        self.password = ""

        self.password_alt_tab_delay_ms = 500
        self.password_key_interval_ms = 50

        self.password_action_lock = threading.Lock()

        self.config_window = None

        self.password_visible = False

        # ----------------------------------------------------
        # CARREGAR CONFIG
        # ----------------------------------------------------

        self.load_config()

        self.alt_tab_checkbox_var = tk.BooleanVar(
            value=self.enable_alt_tab
        )

        # ----------------------------------------------------
        # INTERFACE
        # ----------------------------------------------------

        self.status_label = tk.Label(
            root,
            text=
            "Pressione F8 ou clique em Iniciar"
        )

        self.status_label.pack(
            pady=(10, 5)
        )

        self.start_button = tk.Button(
            root,
            text="Iniciar",
            command=self.toggle_clicker
        )

        self.start_button.pack(
            pady=3
        )

        # ----------------------------------------------------
        # SENHA
        # ----------------------------------------------------

        password_frame = tk.Frame(
            root
        )

        password_frame.pack(
            pady=(8, 3)
        )

        tk.Label(
            password_frame,
            text="Senha:"
        ).pack(
            side=tk.LEFT,
            padx=(0, 5)
        )

        self.password_entry = tk.Entry(
            password_frame,
            width=28,
            show="•"
        )

        self.password_entry.pack(
            side=tk.LEFT
        )

        if self.password:

            self.password_entry.insert(
                0,
                self.password
            )

        self.show_password_button = tk.Button(
            password_frame,
            text="👁",
            width=3,
            command=
            self.toggle_password_visibility
        )

        self.show_password_button.pack(
            side=tk.LEFT,
            padx=(4, 0)
        )

        self.send_password_button = tk.Button(
            password_frame,
            text="Enviar",
            command=
            self.send_password_with_alt_tab
        )

        self.send_password_button.pack(
            side=tk.LEFT,
            padx=(4, 0)
        )

        self.password_info_label = tk.Label(
            root,
            text="F9: digitar senha + Enter",
            fg="gray"
        )

        self.password_info_label.pack(
            pady=(1, 2)
        )

        # ----------------------------------------------------
        # TIMER
        # ----------------------------------------------------

        self.timer_label = tk.Label(
            root,
            text=
            "Tempo restante: 00:00"
        )

        self.timer_label.pack(
            pady=3
        )

        # ----------------------------------------------------
        # ENGRENAGEM
        # ----------------------------------------------------

        engrenagem_btn = tk.Button(
            root,
            text="⚙️",
            command=self.open_settings,
            bd=0,
            font=("Arial", 12)
        )

        engrenagem_btn.place(
            relx=1.0,
            rely=0.0,
            anchor="ne",
            x=-5,
            y=5
        )

        # ----------------------------------------------------
        # TIMER
        # ----------------------------------------------------

        self.timer = TimerController(
            self.timer_label,
            self.root
        )

        # ----------------------------------------------------
        # HOTKEYS
        # ----------------------------------------------------

        debug("Registrando F8...")

        keyboard.add_hotkey(
            "F8",
            self.toggle_clicker
        )

        debug("F8 registrado.")

        debug("Registrando F9...")

        keyboard.add_hotkey(
            "F9",
            self.send_password_f9
        )

        debug("F9 registrado.")

        # ----------------------------------------------------
        # THREAD DO AUTO CLICKER
        # ----------------------------------------------------

        self.clicker_thread = threading.Thread(
            target=self.auto_clicker_loop,
            daemon=True
        )

        self.clicker_thread.start()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.cleanup
        )

        debug("Programa iniciado com sucesso.")
        debug("================================================")

    # ========================================================
    # SENHA
    # ========================================================

    def toggle_password_visibility(self):

        self.password_visible = (
            not self.password_visible
        )

        if self.password_visible:

            self.password_entry.config(
                show=""
            )

            self.show_password_button.config(
                text="🙈"
            )

        else:

            self.password_entry.config(
                show="•"
            )

            self.show_password_button.config(
                text="👁"
            )

    def get_current_password(self):

        password = self.password_entry.get()

        debug(
            f"[PASSWORD] Campo possui "
            f"{len(password)} caracteres."
        )

        return password

    # ========================================================
    # F9
    #
    # F9:
    # senha -> Enter
    #
    # NÃO FAZ ALT+TAB
    # ========================================================

    def send_password_f9(self):

        debug("")
        debug("----------------------------------------")
        debug("[F9] F9 detectado")
        debug("----------------------------------------")

        password = self.get_current_password()

        if not password:

            debug(
                "[F9] Senha vazia. Nada a fazer."
            )

            return

        threading.Thread(
            target=self._type_password_action,
            args=(
                password,
                False,
                "F9"
            ),
            daemon=True
        ).start()

    # ========================================================
    # BOTÃO ENVIAR
    #
    # Alt+Tab
    # Enter
    # senha
    # Enter
    # ========================================================

    def send_password_with_alt_tab(self):

        debug("")
        debug("----------------------------------------")
        debug("[BUTTON] Botão Enviar pressionado")
        debug("----------------------------------------")

        password = self.get_current_password()

        if not password:

            debug(
                "[BUTTON] Senha vazia. Nada a fazer."
            )

            return

        self.password = password

        self.save_config_safely()

        threading.Thread(
            target=self._type_password_action,
            args=(
                password,
                True,
                "BUTTON"
            ),
            daemon=True
        ).start()

    # ========================================================
    # EXECUTAR SEQUÊNCIA DE SENHA
    # ========================================================

    def _type_password_action(
        self,
        password,
        use_alt_tab,
        source
    ):

        debug(
            f"[{source}] Thread iniciada."
        )

        if not self.password_action_lock.acquire(
            blocking=False
        ):

            debug(
                f"[{source}] "
                f"Outra sequência já está executando."
            )

            return

        try:

            # ------------------------------------------------
            # ALT+TAB
            # ------------------------------------------------

            if use_alt_tab:

                debug(
                    f"[{source}] Enviando Alt+Tab..."
                )

                keyboard.press("alt")

                time.sleep(0.05)

                keyboard.press_and_release(
                    "tab"
                )

                time.sleep(0.05)

                keyboard.release("alt")

                debug(
                    f"[{source}] Alt+Tab enviado."
                )

                delay = (
                    self.password_alt_tab_delay_ms
                    / 1000.0
                )

                debug(
                    f"[{source}] "
                    f"Aguardando "
                    f"{self.password_alt_tab_delay_ms} ms..."
                )

                time.sleep(delay)

                # ------------------------------------------------
                # PRIMEIRO ENTER
                # ------------------------------------------------

                debug(
                    f"[{source}] "
                    f"Enviando primeiro Enter..."
                )

                result = self.send_enter()

                debug(
                    f"[{source}] "
                    f"Resultado Enter: {result}"
                )

            # ------------------------------------------------
            # SENHA
            # ------------------------------------------------

            debug(
                f"[{source}] "
                f"Começando digitação de "
                f"{len(password)} caracteres..."
            )

            self.type_text(
                password,
                source
            )

            # ------------------------------------------------
            # ENTER FINAL
            # ------------------------------------------------

            debug(
                f"[{source}] "
                f"Enviando Enter final..."
            )

            result = self.send_enter()

            debug(
                f"[{source}] "
                f"Resultado Enter final: {result}"
            )

            debug(
                f"[{source}] "
                f"SEQUÊNCIA CONCLUÍDA."
            )

        except Exception as e:

            debug(
                f"[{source}] ERRO: {repr(e)}"
            )

        finally:

            self.password_action_lock.release()

            debug(
                f"[{source}] Lock liberado."
            )

    # ========================================================
    # DIGITAR TEXTO
    # ========================================================

    def type_text(
        self,
        text,
        source
    ):

        total = len(text)

        for index, char in enumerate(
            text,
            start=1
        ):

            debug(
                f"[{source}] "
                f"Caractere {index}/{total}: "
                f"Unicode U+{ord(char):04X}"
            )

            # ------------------------------------------------
            # LETRA MAIÚSCULA
            # ------------------------------------------------

            if char.isupper():

                lower_char = char.lower()

                if lower_char in KEY_MAP:

                    vk = KEY_MAP[
                        lower_char
                    ]

                    shift_down = press_shift()

                    key_result = press_key(
                        vk
                    )

                    shift_up = release_shift()

                    debug(
                        f"[{source}] "
                        f"Shift={shift_down}, "
                        f"Key={key_result}, "
                        f"ShiftUp={shift_up}"
                    )

                else:

                    debug(
                        f"[{source}] "
                        f"Maiúscula não mapeada."
                    )

            # ------------------------------------------------
            # CARACTERE COM SHIFT
            # ------------------------------------------------

            elif char in SHIFT_MAP:

                base_char = SHIFT_MAP[
                    char
                ]

                vk = KEY_MAP.get(
                    base_char
                )

                if vk is None:

                    debug(
                        f"[{source}] "
                        f"Caractere não mapeado: "
                        f"U+{ord(char):04X}"
                    )

                else:

                    shift_down = press_shift()

                    key_result = press_key(
                        vk
                    )

                    shift_up = release_shift()

                    debug(
                        f"[{source}] "
                        f"Shift={shift_down}, "
                        f"Key={key_result}, "
                        f"ShiftUp={shift_up}"
                    )

            # ------------------------------------------------
            # CARACTERE NORMAL
            # ------------------------------------------------

            elif char in KEY_MAP:

                vk = KEY_MAP[
                    char
                ]

                result = press_key(
                    vk
                )

                debug(
                    f"[{source}] "
                    f"Key result={result}"
                )

            else:

                debug(
                    f"[{source}] "
                    f"CARACTERE NÃO SUPORTADO: "
                    f"U+{ord(char):04X}"
                )

            # ------------------------------------------------
            # DELAY ENTRE TECLAS
            # ------------------------------------------------

            if self.password_key_interval_ms > 0:

                time.sleep(
                    self.password_key_interval_ms
                    / 1000.0
                )

    # ========================================================
    # ENTER
    # ========================================================

    def send_enter(self):

        VK_RETURN = 0x0D

        down = send_key(
            VK_RETURN,
            False
        )

        time.sleep(0.02)

        up = send_key(
            VK_RETURN,
            True
        )

        return down, up

    # ========================================================
    # AUTO CLICKER
    # ========================================================

    def toggle_clicker(self):

        self.running = not self.running

        self.status_label.config(
            text=
            f"Auto Clicker: "
            f"{'Iniciado' if self.running else 'Pausado'}"
        )

        if self.running:

            print(
                f"Iniciando cliques em "
                f"({self.target_x}, "
                f"{self.target_y})..."
            )

            self.perform_click()

            self.start_timer()

        else:

            print(
                "Auto Clicker pausado."
            )

            self.timer.stop()

            self.timer_label.config(
                text=
                "Tempo restante: 00:00"
            )

    def start_timer(self):

        total_seconds = (
            self.minutes * 60
            + self.seconds
        )

        self.timer.start(
            total_seconds
        )

    def perform_click(self):

        debug(
            f"[MOUSE] Movendo para "
            f"X={self.target_x}, "
            f"Y={self.target_y}"
        )

        user32.SetCursorPos(
            self.target_x,
            self.target_y
        )

        result = self.send_click()

        if not result:

            debug(
                "[MOUSE] Clique falhou."
            )

            return

        time.sleep(0.1)

        if self.enable_alt_tab:

            debug(
                "[MOUSE] Enviando Alt+Tab..."
            )

            keyboard.send(
                "alt+tab"
            )

    def send_click(self):

        """
        Envia um clique esquerdo.

        Esta função usa uma chamada própria de SendInput
        para o mouse, separada da implementação usada
        pelo teclado.
        """

        INPUT_MOUSE = 0

        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004

        if ctypes.sizeof(
            ctypes.c_void_p
        ) == 8:

            ULONG_PTR = ctypes.c_uint64

        else:

            ULONG_PTR = ctypes.c_uint32

        class MOUSEINPUT_LOCAL(
            ctypes.Structure
        ):

            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            ]

        class INPUT_MOUSE_LOCAL(
            ctypes.Structure
        ):

            _fields_ = [
                ("type", wintypes.DWORD),
                ("mi", MOUSEINPUT_LOCAL),
            ]

        inputs = (
            INPUT_MOUSE_LOCAL * 2
        )()

        # ----------------------------------------------------
        # LEFT DOWN
        # ----------------------------------------------------

        inputs[0].type = INPUT_MOUSE

        inputs[0].mi = MOUSEINPUT_LOCAL(
            0,
            0,
            0,
            MOUSEEVENTF_LEFTDOWN,
            0,
            0
        )

        # ----------------------------------------------------
        # LEFT UP
        # ----------------------------------------------------

        inputs[1].type = INPUT_MOUSE

        inputs[1].mi = MOUSEINPUT_LOCAL(
            0,
            0,
            0,
            MOUSEEVENTF_LEFTUP,
            0,
            0
        )

        # ----------------------------------------------------
        # IMPORTANTE
        #
        # Não usamos a versão tipada global de SendInput
        # aqui porque ela está configurada para INPUT de
        # teclado.
        # ----------------------------------------------------

        mouse_user32 = ctypes.WinDLL(
            "user32",
            use_last_error=True
        )

        mouse_send_input = (
            mouse_user32.SendInput
        )

        mouse_send_input.argtypes = [
            wintypes.UINT,
            ctypes.c_void_p,
            ctypes.c_int
        ]

        mouse_send_input.restype = (
            wintypes.UINT
        )

        result = mouse_send_input(
            2,
            ctypes.cast(
                inputs,
                ctypes.c_void_p
            ),
            ctypes.sizeof(
                INPUT_MOUSE_LOCAL
            )
        )

        if result != 2:

            error = ctypes.get_last_error()

            debug(
                f"[MOUSE] SendInput ERRO: "
                f"resultado={result}, "
                f"LastError={error}"
            )

            return False

        debug(
            "[MOUSE] "
            "Clique enviado com sucesso."
        )

        return True

    def auto_clicker_loop(self):

        while True:

            if self.running:

                delay = (
                    self.minutes * 60
                    + self.seconds
                )

                time.sleep(
                    delay
                )

                if self.running:

                    self.perform_click()

                    if self.running:

                        self.start_timer()

            else:

                time.sleep(
                    0.1
                )

    # ========================================================
    # CONFIGURAÇÕES
    # ========================================================

    def open_settings(self):

        if (
            self.config_window
            and self.config_window.winfo_exists()
        ):

            self.config_window.focus()

            return

        self.config_window = Toplevel(
            self.root
        )

        self.config_window.title(
            "Configurações"
        )

        self.config_window.geometry(
            "360x410"
        )

        self.config_window.resizable(
            False,
            False
        )

        # ----------------------------------------------------
        # COORDENADAS
        # ----------------------------------------------------

        tk.Label(
            self.config_window,
            text=
            "Coordenadas do clique:"
        ).pack(
            pady=(10, 0)
        )

        self.coord_label = tk.Label(
            self.config_window,
            text=
            f"X: {self.target_x}, "
            f"Y: {self.target_y}"
        )

        self.coord_label.pack()

        tk.Button(
            self.config_window,
            text=
            "Capturar próxima posição do mouse",
            command=
            self.capture_mouse_position
        ).pack(
            pady=10
        )

        # ----------------------------------------------------
        # INTERVALO
        # ----------------------------------------------------

        tk.Label(
            self.config_window,
            text=
            "Intervalo entre cliques:"
        ).pack(
            pady=(10, 0)
        )

        tempo_frame = tk.Frame(
            self.config_window
        )

        tempo_frame.pack()

        tk.Label(
            tempo_frame,
            text="Minutos:"
        ).grid(
            row=0,
            column=0
        )

        self.min_entry = tk.Entry(
            tempo_frame,
            width=5
        )

        self.min_entry.insert(
            0,
            str(self.minutes)
        )

        self.min_entry.grid(
            row=0,
            column=1,
            padx=(3, 10)
        )

        tk.Label(
            tempo_frame,
            text="Segundos:"
        ).grid(
            row=0,
            column=2
        )

        self.sec_entry = tk.Entry(
            tempo_frame,
            width=5
        )

        self.sec_entry.insert(
            0,
            str(self.seconds)
        )

        self.sec_entry.grid(
            row=0,
            column=3
        )

        self.alt_tab_checkbox = tk.Checkbutton(
            self.config_window,
            text=
            "Ativar Alt+Tab do Auto Clicker",
            variable=
            self.alt_tab_checkbox_var
        )

        self.alt_tab_checkbox.pack(
            pady=10
        )

        # ----------------------------------------------------
        # DIVISOR
        # ----------------------------------------------------

        separator = tk.Frame(
            self.config_window,
            height=1,
            bg="#cccccc"
        )

        separator.pack(
            fill="x",
            padx=20,
            pady=5
        )

        # ----------------------------------------------------
        # SENHA
        # ----------------------------------------------------

        tk.Label(
            self.config_window,
            text="Configuração da senha",
            font=("Arial", 10, "bold")
        ).pack(
            pady=(8, 8)
        )

        delay_frame = tk.Frame(
            self.config_window
        )

        delay_frame.pack(
            pady=3
        )

        tk.Label(
            delay_frame,
            text=
            "Delay após Alt+Tab:"
        ).grid(
            row=0,
            column=0
        )

        self.password_delay_entry = tk.Entry(
            delay_frame,
            width=8
        )

        self.password_delay_entry.insert(
            0,
            str(
                self.password_alt_tab_delay_ms
            )
        )

        self.password_delay_entry.grid(
            row=0,
            column=1,
            padx=5
        )

        tk.Label(
            delay_frame,
            text="ms"
        ).grid(
            row=0,
            column=2
        )

        interval_frame = tk.Frame(
            self.config_window
        )

        interval_frame.pack(
            pady=3
        )

        tk.Label(
            interval_frame,
            text=
            "Intervalo entre teclas:"
        ).grid(
            row=0,
            column=0
        )

        self.password_interval_entry = tk.Entry(
            interval_frame,
            width=8
        )

        self.password_interval_entry.insert(
            0,
            str(
                self.password_key_interval_ms
            )
        )

        self.password_interval_entry.grid(
            row=0,
            column=1,
            padx=5
        )

        tk.Label(
            interval_frame,
            text="ms"
        ).grid(
            row=0,
            column=2
        )

        # ----------------------------------------------------
        # SALVAR
        # ----------------------------------------------------

        tk.Button(
            self.config_window,
            text="Salvar",
            command=
            self.save_config
        ).pack(
            pady=15
        )

        self.config_window.protocol(
            "WM_DELETE_WINDOW",
            self.close_config_window
        )

    def close_config_window(self):

        if self.config_window:

            self.config_window.destroy()

        self.config_window = None

    # ========================================================
    # CAPTURA POSIÇÃO
    # ========================================================

    def capture_mouse_position(self):

        self.coord_label.config(
            text=
            "Aguardando clique..."
        )

        overlay = Toplevel(
            self.root
        )

        overlay.overrideredirect(
            True
        )

        overlay.attributes(
            "-topmost",
            True
        )

        overlay.configure(
            bg="white"
        )

        label_overlay = tk.Label(
            overlay,
            text="",
            bg="white",
            font=("Arial", 8)
        )

        label_overlay.pack()

        def update_position():

            if not overlay.winfo_exists():
                return

            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()

            overlay.geometry(
                f"+{x + 10}+{y + 20}"
            )

            label_overlay.config(
                text=
                f"X: {x}, Y: {y}"
            )

            self.root.after(
                50,
                update_position
            )

        update_position()

        def on_click(
            x,
            y,
            button,
            pressed
        ):

            if pressed:

                self.target_x = x
                self.target_y = y

                self.coord_label.config(
                    text=
                    f"Capturado: "
                    f"X={x}, Y={y}"
                )

                if overlay.winfo_exists():

                    overlay.destroy()

                listener.stop()

        listener = mouse.Listener(
            on_click=on_click
        )

        listener.start()

    # ========================================================
    # SALVAR CONFIG
    # ========================================================

    def save_config(self):

        try:

            self.minutes = int(
                self.min_entry.get()
            )

            self.seconds = int(
                self.sec_entry.get()
            )

            self.password_alt_tab_delay_ms = int(
                self.password_delay_entry.get()
            )

            self.password_key_interval_ms = int(
                self.password_interval_entry.get()
            )

            if (
                self.minutes < 0
                or self.seconds < 0
                or (
                    self.minutes * 60
                    + self.seconds
                    <= 0
                )
            ):

                raise ValueError

            if (
                self.password_alt_tab_delay_ms < 0
                or self.password_key_interval_ms < 0
            ):

                raise ValueError

        except ValueError:

            messagebox.showerror(
                "Valor inválido",
                "Verifique os valores informados."
            )

            return

        self.enable_alt_tab = (
            self.alt_tab_checkbox_var.get()
        )

        self.password = (
            self.get_current_password()
        )

        try:

            self.save_to_file()

        except Exception as e:

            messagebox.showerror(
                "Erro",
                str(e)
            )

            return

        self.close_config_window()

    def save_config_safely(self):

        try:

            self.password = (
                self.get_current_password()
            )

            self.save_to_file()

        except Exception as e:

            debug(
                f"[CONFIG] Erro ao salvar: {e}"
            )

    def save_to_file(self):

        encrypted_password = (
            encrypt_password(
                self.password
            )
        )

        config = {

            "x": self.target_x,
            "y": self.target_y,

            "minutes": self.minutes,
            "seconds": self.seconds,

            "enable_alt_tab":
                self.enable_alt_tab,

            "password":
                encrypted_password,

            "password_alt_tab_delay_ms":
                self.password_alt_tab_delay_ms,

            "password_key_interval_ms":
                self.password_key_interval_ms
        }

        with open(
            "config.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                config,
                f,
                ensure_ascii=False
            )

        debug(
            "[CONFIG] config.json atualizado."
        )

    # ========================================================
    # CARREGAR CONFIG
    # ========================================================

    def load_config(self):

        debug(
            "[CONFIG] Procurando config.json..."
        )

        if not os.path.exists(
            "config.json"
        ):

            debug(
                "[CONFIG] config.json "
                "não encontrado."
            )

            return

        try:

            with open(
                "config.json",
                "r",
                encoding="utf-8"
            ) as f:

                config = json.load(f)

            self.target_x = config.get(
                "x",
                -994
            )

            self.target_y = config.get(
                "y",
                112
            )

            self.minutes = config.get(
                "minutes",
                2
            )

            self.seconds = config.get(
                "seconds",
                30
            )

            self.enable_alt_tab = config.get(
                "enable_alt_tab",
                True
            )

            self.password_alt_tab_delay_ms = config.get(
                "password_alt_tab_delay_ms",
                500
            )

            self.password_key_interval_ms = config.get(
                "password_key_interval_ms",
                50
            )

            encrypted_password = config.get(
                "password",
                ""
            )

            if encrypted_password:

                self.password = (
                    decrypt_password(
                        encrypted_password
                    )
                )

                if self.password:

                    debug(
                        "[CONFIG] "
                        "Senha carregada com sucesso."
                    )

            debug(
                f"[CONFIG] Coordenadas: "
                f"X={self.target_x}, "
                f"Y={self.target_y}"
            )

            debug(
                f"[CONFIG] Intervalo: "
                f"{self.minutes}m "
                f"{self.seconds}s"
            )

            debug(
                f"[CONFIG] "
                f"Alt+Tab autoclicker: "
                f"{self.enable_alt_tab}"
            )

            debug(
                f"[CONFIG] "
                f"Delay Alt+Tab senha: "
                f"{self.password_alt_tab_delay_ms} ms"
            )

            debug(
                f"[CONFIG] "
                f"Intervalo teclas: "
                f"{self.password_key_interval_ms} ms"
            )

        except Exception as e:

            debug(
                f"[CONFIG] "
                f"Erro ao carregar: {repr(e)}"
            )

    # ========================================================
    # ENCERRAR
    # ========================================================

    def cleanup(self):

        debug(
            "[APP] Encerrando Auto Clicker..."
        )

        self.running = False

        self.timer.stop()

        try:

            keyboard.remove_hotkey(
                "F8"
            )

        except Exception:
            pass

        try:

            keyboard.remove_hotkey(
                "F9"
            )

        except Exception:
            pass

        try:

            self.password = (
                self.get_current_password()
            )

            self.save_to_file()

        except Exception as e:

            debug(
                f"[CONFIG] "
                f"Erro ao salvar: {repr(e)}"
            )

        self.root.destroy()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    debug(
        "[DEBUG] Executando arquivo Python..."
    )

    root = tk.Tk()

    app = AutoClickerApp(
        root
    )

    root.mainloop()