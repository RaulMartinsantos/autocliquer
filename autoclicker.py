import tkinter as tk
from tkinter import Toplevel
import threading
import keyboard
import time
import ctypes
from ctypes import wintypes
from pynput import mouse
import json
import os

if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_uint32

class TimerController:
    def __init__(self, label):
        self.label = label
        self._stop_event = threading.Event()
        self.thread = None

    def start(self, duration_sec):
        self.stop()
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_timer, args=(duration_sec,), daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.1)

    def _run_timer(self, total_seconds):
        for remaining in range(total_seconds, 0, -1):
            if self._stop_event.is_set():
                break
            minutes, seconds = divmod(remaining, 60)
            self.label.config(text=f"Tempo restante: {minutes:02}:{seconds:02}")
            time.sleep(1)
        self.label.config(text="Tempo restante: 00:00")

class AutoClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker Personalizável")
        self.root.geometry("300x117")

        self.running = False
        self.target_x, self.target_y = 100, 100
        self.minutes, self.seconds = 2, 10
        self.enable_alt_tab = True
        self.alt_tab_checkbox_var = tk.BooleanVar(value=self.enable_alt_tab)

        self.load_config()

        self.status_label = tk.Label(root, text="Pressione F8 ou clique em Iniciar")
        self.status_label.pack(pady=10)

        self.start_button = tk.Button(root, text="Iniciar", command=self.toggle_clicker)
        self.start_button.pack(pady=5)

        self.timer_label = tk.Label(root, text="Tempo restante: 00:00")
        self.timer_label.pack(pady=5)

        engrenagem_btn = tk.Button(root, text="⚙️", command=self.open_settings, bd=0, font=("Arial", 12))
        engrenagem_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)

        self.timer = TimerController(self.timer_label)

        keyboard.add_hotkey("F8", self.toggle_clicker)

        self.clicker_thread = threading.Thread(target=self.auto_clicker_loop, daemon=True)
        self.clicker_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.cleanup)

    def toggle_clicker(self):
        self.running = not self.running
        self.status_label.config(text=f"Auto Clicker: {'Iniciado' if self.running else 'Pausado'}")

        if self.running:
            print(f"Iniciando cliques em ({self.target_x}, {self.target_y})...")
            self.perform_click()
            self.start_timer()
        else:
            print("Auto Clicker pausado.")
            self.timer.stop()
            self.timer_label.config(text="Tempo restante: 00:00")

    def start_timer(self):
        total_seconds = self.minutes * 60 + self.seconds
        self.timer.start(total_seconds)

    def perform_click(self):
        ctypes.windll.user32.SetCursorPos(self.target_x, self.target_y)
        self.send_click()
        time.sleep(0.1)
        if self.enable_alt_tab:
            keyboard.send("alt+tab")

    def send_click(self):
        INPUT_MOUSE = 0
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = (("dx", wintypes.LONG),
                        ("dy", wintypes.LONG),
                        ("mouseData", wintypes.DWORD),
                        ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD),
                        ("dwExtraInfo", ULONG_PTR))

        class INPUT(ctypes.Structure):
            _fields_ = (("type", wintypes.DWORD),
                        ("mi", MOUSEINPUT))

        inputs = (INPUT * 2)()
        inputs[0].type = INPUT_MOUSE
        inputs[0].mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0)
        inputs[1].type = INPUT_MOUSE
        inputs[1].mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0)
        ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

    def auto_clicker_loop(self):
        while True:
            if self.running:
                delay = self.minutes * 60 + self.seconds
                time.sleep(delay)
                if self.running:
                    self.perform_click()
                    self.start_timer()
            else:
                time.sleep(0.1)

    def open_settings(self):
        self.config_window = Toplevel(self.root)
        self.config_window.title("Configurações")
        self.config_window.geometry("300x250")

        tk.Label(self.config_window, text="Coordenadas do clique:").pack(pady=(10, 0))
        self.coord_label = tk.Label(self.config_window, text=f"X: {self.target_x}, Y: {self.target_y}")
        self.coord_label.pack()

        tk.Button(self.config_window, text="Capturar próxima posição do mouse", command=self.capture_mouse_position).pack(pady=10)

        tk.Label(self.config_window, text="Intervalo entre cliques:").pack(pady=(10, 0))
        tempo_frame = tk.Frame(self.config_window)
        tempo_frame.pack()

        tk.Label(tempo_frame, text="Minutos:").grid(row=0, column=0)
        self.min_entry = tk.Entry(tempo_frame, width=5)
        self.min_entry.insert(0, str(self.minutes))
        self.min_entry.grid(row=0, column=1)

        tk.Label(tempo_frame, text="Segundos:").grid(row=0, column=2)
        self.sec_entry = tk.Entry(tempo_frame, width=5)
        self.sec_entry.insert(0, str(self.seconds))
        self.sec_entry.grid(row=0, column=3)

        self.alt_tab_checkbox = tk.Checkbutton(self.config_window, text="Ativar Alt+Tab", variable=self.alt_tab_checkbox_var)
        self.alt_tab_checkbox.pack(pady=10)

        tk.Button(self.config_window, text="Salvar", command=self.save_config).pack(pady=15)

    def capture_mouse_position(self):
        self.coord_label.config(text="Aguardando clique...")

        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="white")

        label_overlay = tk.Label(overlay, text="", bg="white", font=("Arial", 8))
        label_overlay.pack()

        def update_position():
            if not overlay.winfo_exists():
                return
            x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
            overlay.geometry(f"+{x + 10}+{y + 20}")
            label_overlay.config(text=f"X: {x}, Y: {y}")
            self.root.after(50, update_position)

        update_position()

        def on_click(x, y, button, pressed):
            if pressed:
                self.target_x, self.target_y = x, y
                self.coord_label.config(text=f"Capturado: X={x}, Y={y}")
                if overlay.winfo_exists():
                    overlay.destroy()
                listener.stop()

        listener = mouse.Listener(on_click=on_click)
        listener.start()

    def save_config(self):
        try:
            self.minutes = int(self.min_entry.get())
            self.seconds = int(self.sec_entry.get())
            if self.minutes * 60 + self.seconds <= 0:
                raise ValueError
        except ValueError:
            return

        self.enable_alt_tab = self.alt_tab_checkbox_var.get()
        self.save_to_file()
        self.config_window.destroy()

    def save_to_file(self):
        with open("config.json", "w") as f:
            json.dump({
                "x": self.target_x,
                "y": self.target_y,
                "minutes": self.minutes,
                "seconds": self.seconds,
                "enable_alt_tab": self.enable_alt_tab
            }, f)

    def load_config(self):
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
                self.target_x = config.get("x", 100)
                self.target_y = config.get("y", 100)
                self.minutes = config.get("minutes", 2)
                self.seconds = config.get("seconds", 10)
                self.enable_alt_tab = config.get("enable_alt_tab", True)
                self.alt_tab_checkbox_var.set(self.enable_alt_tab)

    def cleanup(self):
        print("Encerrando Auto Clicker...")
        self.running = False
        self.timer.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClickerApp(root)
    root.mainloop()
