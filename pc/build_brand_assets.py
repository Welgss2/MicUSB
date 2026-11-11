"""Render MicUSB's own vector identity into crisp app, tray, and Windows icons."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
INK = "#101114"
CREAM = "#D7F5EA"
MINT = "#65D6AC"

def make_mark(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size / 256
    def box(values): return tuple(round(v*s) for v in values)
    d.rounded_rectangle(box((8,8,248,248)), radius=round(62*s), fill=INK)
    for x, y0, y1 in ((68,116,140),(116,88,168),(164,116,140)):
        d.rounded_rectangle(box((x,y0,x+24,y1)), radius=round(12*s), fill=CREAM)
    d.arc(box((52,121,204,222)), start=18, end=162, fill=MINT, width=max(2,round(10*s)))
    d.ellipse(box((121,200,135,214)), fill=MINT)
    return im

make_mark(1024).save(ROOT / "micusb-logo.png", optimize=True)
sizes = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
make_mark(1024).save(ROOT / "micusb.ico", format="ICO", sizes=[(s,s) for s in sizes])
make_mark(256).save(ROOT / "micusb-tray.png", optimize=True)
