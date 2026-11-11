"""
Recebe o microfone do iPhone pelo cabo USB e joga no VB-Cable.
Detecta o iPhone sozinho: pode abrir antes de plugar o cabo.
Requisitos: pip install pymobiledevice3 sounddevice
"""
import socket, subprocess, sys, time
import sounddevice as sd

PORT = 5000
RATE = 48000
OUT_NAME = "CABLE In"      # nome atual do endpoint VB-CABLE; nos apps use "CABLE Output" como microfone


def find_output():
    for i, d in enumerate(sd.query_devices()):
        if OUT_NAME.lower() in d["name"].lower() and d["max_output_channels"] > 0:
            return i
    return None


def start_forward():
    return subprocess.Popen(
        [sys.executable, "-m", "pymobiledevice3", "usbmux", "forward", str(PORT), str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def stream(dev):
    s = socket.create_connection(("127.0.0.1", PORT), timeout=3)
    s.settimeout(5)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    with sd.RawOutputStream(samplerate=RATE, channels=1, dtype="int16",
                            device=dev, latency="low") as out:
        print("Conectado. Áudio fluindo.")
        pending = b""
        while True:
            data = s.recv(4096)
            if not data:
                break
            data = pending + data
            # TCP não preserva os limites dos blocos enviados pelo iPhone.
            # Mantém qualquer byte final até chegar o restante da amostra PCM.
            usable = len(data) & ~1
            if usable:
                out.write(data[:usable])
            pending = data[usable:]


def main():
    dev = find_output()
    if dev is None:
        print(f"VB-Cable não encontrado (procurei '{OUT_NAME}'). Instale em vb-audio.com/Cable e reinicie o PC.")
        sys.exit(1)
    print("Aguardando iPhone (abra o app MicUSB nele)...")
    fwd = None
    try:
        while True:
            if fwd is None or fwd.poll() is not None:
                fwd = start_forward()
                time.sleep(1.5)
            try:
                stream(dev)
            except (OSError, socket.timeout):
                pass
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if fwd and fwd.poll() is None:
            fwd.terminate()


if __name__ == "__main__":
    main()
