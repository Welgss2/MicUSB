"""MicUSB: microfone do iPhone por USB com controles de áudio no Windows."""
import math
import queue
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import argparse
import pystray
from PIL import Image, ImageDraw

import numpy as np
import sounddevice as sd
from deepfilter_stream import DeepFilterModel

PORT = 5000
RATE = 48000
OUT_NAME = "CABLE In"
BG = "#101719"
CARD = "#182326"
CARD2 = "#202e31"
TEXT = "#f1f7f5"
MUTED = "#9aadaa"
ACCENT = "#42d6ae"


class VoiceProcessor:
    """DeepFilterNet3, passa-altas, ganho/limitador e gate ajustável."""
    def __init__(self, on_level=None):
        self.model = DeepFilterModel(intra_op_num_threads=1)
        self._lock = threading.Lock()
        self._strength = "Média"
        self._attenuation = {"Leve": 10.0, "Média": 18.0, "Forte": 30.0}
        self.denoiser = self.model.new_stream(atten_lim_db=self._attenuation[self._strength])
        self.gain_db = 3.0
        self.auto_gain_max_db = 12.0
        self.auto_gain = 1.0
        self.limiter_gain = 1.0
        self.gate_db = -65.0
        self.gate_gain = 1.0
        self.treble_db = -2.5
        self.tone_lp = 0.0
        self.tone_alpha = 1.0 - math.exp(-2.0 * math.pi * 3600 / RATE)
        self.hpf_enabled = True
        self.hp_prev_x = 0.0
        self.hp_prev_y = 0.0
        self.hp_alpha = 1.0 - (2.0 * math.pi * 100 / RATE)
        self.on_level = on_level or (lambda _level: None)
        self._test_until = 0.0
        self._test_peak = 0.0
        self.test_result = None

    def set_strength(self, strength):
        with self._lock:
            if strength != self._strength:
                self.denoiser = self.model.new_stream(atten_lim_db=self._attenuation[strength])
                self._strength = strength

    def start_test(self):
        self._test_peak = 0.0
        self.test_result = None
        self._test_until = time.monotonic() + 5.0

    def process(self, pcm):
        x = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        if self.hpf_enabled:
            y = np.empty_like(x)
            prev_x, prev_y, alpha = self.hp_prev_x, self.hp_prev_y, self.hp_alpha
            for i, sample in enumerate(x):
                prev_y = alpha * (prev_y + sample - prev_x)
                prev_x = sample
                y[i] = prev_y
            self.hp_prev_x, self.hp_prev_y = float(prev_x), float(prev_y)
        else:
            y = x

        with self._lock:
            clean = self.denoiser.process(y, sr=RATE)

        # Broad, gentle high shelf: lowers sharpness while preserving speech presence.
        low = np.empty_like(clean)
        state = self.tone_lp
        alpha = self.tone_alpha
        for i, sample in enumerate(clean):
            state += alpha * (float(sample) - state)
            low[i] = state
        self.tone_lp = state
        high_gain = 10.0 ** (self.treble_db / 20.0)
        clean = low + (clean - low) * high_gain

        rms = float(np.sqrt(np.mean(clean * clean) + 1e-12))
        level_db = max(-60.0, 20.0 * math.log10(max(rms, 1e-6)))
        self.on_level(level_db)
        now = time.monotonic()
        if now < self._test_until:
            self._test_peak = max(self._test_peak, level_db)
        elif self._test_until and self.test_result is None:
            self.test_result = self._test_peak
            self._test_until = 0.0

        voice_active = level_db >= self.gate_db
        target = 1.0 if voice_active else 0.025
        attack = math.exp(-1.0 / (0.008 * RATE))
        release = math.exp(-1.0 / (0.090 * RATE))
        gated = np.empty_like(clean)
        gain = self.gate_gain
        for i, sample in enumerate(clean):
            coeff = attack if target > gain else release
            gain = target + coeff * (gain - target)
            gated[i] = sample * gain
        self.gate_gain = gain
        # Slow, capped AGC raises quieter speech after denoising; it rests during silence.
        gated_rms = float(np.sqrt(np.mean(gated * gated) + 1e-12))
        auto_target = 1.0
        if voice_active and gated_rms > 1e-5 and self.auto_gain_max_db > 0:
            desired = 10.0 ** (-20.0 / 20.0) / gated_rms
            auto_target = min(10.0 ** (self.auto_gain_max_db / 20.0), max(1.0, desired))
        auto_coeff = math.exp(-len(gated) / ((0.220 if auto_target > self.auto_gain else 0.550) * RATE))
        self.auto_gain = auto_target + auto_coeff * (self.auto_gain - auto_target)
        gain_linear = self.auto_gain * (10.0 ** (self.gain_db / 20.0))
        amplified = gated * gain_linear
        peak = float(np.max(np.abs(amplified))) if amplified.size else 0.0
        limiter_target = min(1.0, 0.98 / peak) if peak > 0.98 else 1.0
        if limiter_target < self.limiter_gain:
            self.limiter_gain = limiter_target
        else:
            limiter_coeff = math.exp(-len(amplified) / (0.120 * RATE))
            self.limiter_gain = limiter_target + limiter_coeff * (self.limiter_gain - limiter_target)
        clean = np.clip(amplified * self.limiter_gain, -0.98, 0.98)
        return (clean * 32767.0).astype("<i2").tobytes()


def find_output():
    for i, device in enumerate(sd.query_devices()):
        if OUT_NAME.lower() in device["name"].lower() and device["max_output_channels"] > 0:
            return i
    return None


def start_forward():
    return subprocess.Popen(
        [sys.executable, "-m", "pymobiledevice3", "usbmux", "forward", str(PORT), str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


class MicUSBApp:
    def __init__(self, root, start_hidden=False):
        self.root = root
        self.root.title("MicUSB — Controle de voz")
        self.root.geometry("540x820")
        self.root.minsize(480, 650)
        self.root.configure(bg=BG)
        self.events = queue.Queue()
        self.alive = True
        self.start_hidden = start_hidden
        self.tray_icon = None
        self.processor = None
        self.forwarder = None
        self.stream_thread = None
        self.level = tk.DoubleVar(value=0)
        self.level_text = tk.StringVar(value="-60 dBFS")
        self.gain_db = tk.DoubleVar(value=3)
        self.auto_gain_db = tk.DoubleVar(value=12)
        self.gate_db = tk.DoubleVar(value=-65)
        self.treble_db = tk.DoubleVar(value=-2.5)
        self.strength = tk.StringVar(value="Média")
        self.hpf_enabled = tk.BooleanVar(value=True)
        self.echo_enabled = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Iniciando filtro de áudio…")
        self.test_text = tk.StringVar(value="Fale para testar o nível")
        self._build_ui()
        threading.Thread(target=self._initialize, daemon=True).start()
        self.root.after(100, self._poll)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._start_tray()
        if self.start_hidden:
            self.root.after(350, self.root.withdraw)

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Mic.Horizontal.TScale", background=CARD, troughcolor="#344346", sliderthickness=16)
        style.configure("Mic.Horizontal.TProgressbar", troughcolor="#344346", background=ACCENT, bordercolor="#344346", lightcolor=ACCENT, darkcolor=ACCENT)
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(shell, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        outer = tk.Frame(canvas, bg=BG, padx=22, pady=20)
        window_id = canvas.create_window((0, 0), window=outer, anchor="nw")
        outer.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(-1 * int(event.delta / 120), "units"))

        brand = tk.Frame(outer, bg=BG)
        brand.pack(fill="x", pady=(0, 18))
        mark = tk.Canvas(brand, width=54, height=54, bg=BG, highlightthickness=0)
        mark.pack(side="left", padx=(0, 12))
        mark.create_rounded_rectangle = None
        mark.create_oval(2, 2, 52, 52, fill=ACCENT, outline="")
        mark.create_rectangle(24, 12, 30, 32, fill="#10201e", outline="")
        mark.create_arc(16, 22, 38, 44, start=180, extent=180, style="arc", outline="#10201e", width=3)
        mark.create_line(27, 41, 27, 46, fill="#10201e", width=3)
        tk.Label(brand, text="MicUSB", bg=BG, fg=TEXT, font=("Segoe UI Variable Display", 21, "bold")).pack(anchor="w", pady=(1, 0))
        tk.Label(brand, text="Áudio do iPhone, tratado no PC", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        status_bar = tk.Frame(outer, bg=CARD2, padx=12, pady=10)
        status_bar.pack(fill="x", pady=(0, 16))
        tk.Label(status_bar, text="●", bg=CARD2, fg=ACCENT, font=("Segoe UI", 11)).pack(side="left", padx=(0, 8))
        tk.Label(status_bar, textvariable=self.status, bg=CARD2, fg=TEXT, font=("Segoe UI", 9)).pack(side="left", fill="x")

        mic = self._card(outer, "MICROFONE")
        tk.Label(mic, text="Entrada de áudio • iPhone conectado por USB", bg=CARD, fg=TEXT, font=("Segoe UI", 10)).pack(anchor="w", padx=14, pady=(6, 12))
        self._slider(mic, "Ganho de voz", self.gain_db, -12, 24, " dB", self._set_gain)
        self._slider(mic, "Ganho automático (máx.)", self.auto_gain_db, 0, 18, " dB", self._set_auto_gain)
        meter_row = tk.Frame(mic, bg=CARD2, padx=12, pady=10)
        meter_row.pack(fill="x", padx=14, pady=(8, 12))
        self.meter = ttk.Progressbar(meter_row, maximum=60, variable=self.level, style="Mic.Horizontal.TProgressbar")
        self.meter.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Button(meter_row, text="Testar voz", command=self._test, bg=ACCENT, fg="#10201e", activebackground="#6be4c4", activeforeground="#10201e", relief="flat", padx=14, pady=7, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")
        tk.Label(meter_row, textvariable=self.level_text, bg=CARD2, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="right", padx=(0, 8))
        tk.Label(mic, textvariable=self.test_text, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(0, 12))
        self._slider(mic, "Corte de fundo (gate)", self.gate_db, -80, -30, " dB", self._set_gate)
        tk.Label(mic, text="Mais baixo preserva sons fracos • mais alto corta mais ruído, mas pode cortar voz", bg=CARD, fg=MUTED, font=("Segoe UI", 8), wraplength=430, justify="left").pack(fill="x", padx=14, pady=(0, 10))
        self._slider(mic, "Brilho / suavidade", self.treble_db, -8, 3, " dB", self._set_treble)
        tk.Label(mic, text="Reduzir alguns dB suaviza agudos e sons de 's'; aumentar devolve brilho.", bg=CARD, fg=MUTED, font=("Segoe UI", 8), wraplength=430, justify="left").pack(fill="x", padx=14, pady=(0, 10))

        filt = self._card(outer, "FILTROS")
        tk.Label(filt, text="Redução de ruído por IA", bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(6, 2))
        tk.Label(filt, text="DeepFilterNet3 reduz ruído; escolha Forte se a TV estiver alta", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(0, 9))
        choices = tk.Frame(filt, bg=CARD)
        choices.pack(fill="x", padx=10, pady=(0, 12))
        for option in ("Leve", "Média", "Forte"):
            button = tk.Radiobutton(choices, text=option, value=option, variable=self.strength, command=self._set_strength, indicatoron=False, bg=CARD2, fg=MUTED, selectcolor="#252529", activebackground="#252529", activeforeground=TEXT, font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=9)
            button.pack(side="left", fill="x", expand=True, padx=4)
        self._toggle(filt, "Filtro de graves", "Corta vibração, vento e ruído grave", self.hpf_enabled, self._set_hpf)
        tk.Label(filt, text="Para evitar que o som dos alto-falantes volte ao microfone, use fones.", bg=CARD, fg=MUTED, font=("Segoe UI", 8), wraplength=440, justify="left").pack(anchor="w", padx=14, pady=(2, 12))

        tk.Label(outer, text="Saída do PC: CABLE Input → nos apps escolha CABLE Output", bg=BG, fg=MUTED, font=("Segoe UI", 8), wraplength=450, justify="left").pack(anchor="w", pady=(10, 0))

    def _card(self, parent, title):
        box = tk.Frame(parent, bg=CARD, padx=8, pady=8, highlightthickness=1, highlightbackground="#28373a")
        box.pack(fill="x", pady=(0, 12))
        tk.Label(box, text=title, bg=CARD, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=6, pady=(2, 4))
        return box

    def _slider(self, parent, title, variable, low, high, suffix, callback):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=14, pady=(0, 3))
        tk.Label(row, text=title, bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
        value = tk.Label(row, text=f"{int(variable.get())}{suffix}", bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold"))
        value.pack(side="right")
        def changed(v):
            value.configure(text=f"{int(float(v))}{suffix}")
            callback(float(v))
        slider = ttk.Scale(parent, from_=low, to=high, variable=variable, command=changed, style="Mic.Horizontal.TScale")
        slider.pack(fill="x", padx=12, pady=(0, 8))

    def _toggle(self, parent, title, subtitle, variable, callback, disabled=False):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=14, pady=8)
        texts = tk.Frame(row, bg=CARD)
        texts.pack(side="left", fill="x", expand=True)
        tk.Label(texts, text=title, bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(texts, text=subtitle, bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        toggle = tk.Checkbutton(row, variable=variable, command=callback, state="disabled" if disabled else "normal", bg=CARD, fg=ACCENT, selectcolor=CARD2, activebackground=CARD, activeforeground=ACCENT, disabledforeground="#66666b", cursor="hand2")
        toggle.pack(side="right")

    def _initialize(self):
        try:
            self.processor = VoiceProcessor(on_level=lambda db: self.events.put(("level", db)))
            self.events.put(("status", "Filtro pronto — abra o MicUSB no iPhone"))
            self.forwarder = start_forward()
            self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.stream_thread.start()
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _stream_loop(self):
        while self.alive:
            if self.forwarder is None or self.forwarder.poll() is not None:
                self.forwarder = start_forward()
                time.sleep(1.5)
            try:
                self._stream_once()
            except (OSError, socket.timeout, sd.PortAudioError):
                self.events.put(("status", "Aguardando iPhone pelo USB…"))
            except Exception as exc:
                self.events.put(("status", f"Áudio reconectando: {exc}"))
            time.sleep(0.7)

    def _stream_once(self):
        device = find_output()
        if device is None:
            self.events.put(("status", "VB-CABLE não encontrado — instale ou reinicie o PC"))
            time.sleep(2)
            return
        self.events.put(("status", "Conectando ao iPhone…"))
        with socket.create_connection(("127.0.0.1", PORT), timeout=3) as sock:
            sock.settimeout(5)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with sd.RawOutputStream(samplerate=RATE, channels=1, dtype="int16", device=device, latency="low", blocksize=512) as out:
                self.events.put(("status", "Conectado — tratamento de voz ativo"))
                pending = b""
                while self.alive:
                    # Read one 512-sample mono frame (10.7 ms at 48 kHz) at a time.
                    data = sock.recv(1024)
                    if not data:
                        break
                    data = pending + data
                    usable = len(data) - (len(data) % 1024)  # 512 mono int16 samples
                    if usable:
                        out.write(self.processor.process(data[:usable]))
                    pending = data[usable:]

    def _set_gain(self, value):
        if self.processor:
            self.processor.gain_db = value

    def _set_auto_gain(self, value):
        if self.processor:
            self.processor.auto_gain_max_db = value

    def _set_gate(self, value):
        if self.processor:
            self.processor.gate_db = value

    def _set_treble(self, value):
        if self.processor:
            self.processor.treble_db = value

    def _set_strength(self):
        if self.processor:
            self.processor.set_strength(self.strength.get())

    def _set_hpf(self):
        if self.processor:
            self.processor.hpf_enabled = self.hpf_enabled.get()

    def _set_echo(self):
        # Intentionally unavailable without a synchronized render reference.
        self.echo_enabled.set(False)

    def _test(self):
        if not self.processor:
            self.test_text.set("O filtro ainda está iniciando")
            return
        self.processor.start_test()
        self.test_text.set("Fale agora por 5 segundos…")
        self.root.after(5200, self._show_test_result)

    def _show_test_result(self):
        result = self.processor.test_result if self.processor else None
        self.test_text.set("Sem sinal detectado — verifique o iPhone" if result is None or result < -58 else f"Sinal detectado: pico {result:.0f} dBFS")

    def _poll(self):
        if not self.alive:
            return
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self.status.set(value)
                elif kind == "level":
                    self.level.set(max(0, min(60, value + 60)))
                    self.level_text.set(f"{value:.0f} dBFS")
                    if self.processor and self.processor._test_until and time.monotonic() < self.processor._test_until:
                        self.test_text.set("Fale agora por 5 segundos…")
                elif kind == "error":
                    self.status.set("Falha ao iniciar")
                    messagebox.showerror("MicUSB", f"Não foi possível iniciar o filtro de áudio:\n\n{value}\n\nExecute pc\\instalar.bat e tente novamente.")
        except queue.Empty:
            pass
        if self.processor and self.processor.test_result is not None and self.test_text.get().startswith("Fale agora"):
            self._show_test_result()
        self.root.after(100, self._poll)

    def _start_tray(self):
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((5, 5, 59, 59), radius=14, fill=ACCENT)
        draw.rectangle((29, 16, 35, 39), fill="white")
        draw.ellipse((21, 29, 43, 51), outline="white", width=4)
        draw.rectangle((30, 48, 34, 54), fill="white")
        menu = pystray.Menu(
            pystray.MenuItem("Abrir MicUSB", self._tray_show, default=True),
            pystray.MenuItem("Sair", self._tray_quit),
        )
        self.tray_icon = pystray.Icon("MicUSB", image, "MicUSB — microfone ativo", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _tray_show(self, _icon=None, _item=None):
        self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _tray_quit(self, _icon=None, _item=None):
        self.root.after(0, self.quit)

    def close(self):
        # Fechar a janela mantém o áudio ativo; use Sair na bandeja para encerrar.
        self.root.withdraw()

    def quit(self):
        self.alive = False
        if self.forwarder and self.forwarder.poll() is None:
            self.forwarder.terminate()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimized", action="store_true")
    args = parser.parse_args()
    root = tk.Tk()
    try:
        root.iconbitmap(default=str(__import__("pathlib").Path(__file__).with_name("micusb.ico")))
    except tk.TclError:
        pass
    MicUSBApp(root, start_hidden=args.minimized)
    root.mainloop()


if __name__ == "__main__":
    main()
