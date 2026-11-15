from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent
S = 2
W, H = 760, 940
im = Image.new("RGB", (W*S, H*S), "#0b0b0d")
d = ImageDraw.Draw(im)

def font(size, bold=False):
    path = "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
    return ImageFont.truetype(path, size*S)

def rr(box, radius, fill, outline=None, width=1):
    box = tuple(int(v*S) for v in box)
    d.rounded_rectangle(box, radius=radius*S, fill=fill, outline=outline, width=width*S if outline else 1)

def txt(x, y, value, size, fill="#f5f5f7", bold=False):
    d.text((x*S, y*S), value, font=font(size, bold), fill=fill)

def line(points, fill, width=1):
    d.line([(x*S, y*S) for x,y in points], fill=fill, width=width*S)

# Title bar
rr((14, 12, W-14, 64), 15, "#151518", "#242427")
im_icon = Image.open(OUT / "micusb-logo.png").resize((30*S,30*S), Image.Resampling.LANCZOS)
im.paste(im_icon, (28*S, 23*S), im_icon)
txt(68, 23, "MicUSB", 15, bold=True)
txt(145, 26, "VOICE STUDIO", 9, "#8f9097", True)
rr((624, 18, 663, 57), 10, "#202024")
line([(637,38),(650,38)], "#c7c7cd", 2)
rr((668, 18, 707, 57), 10, "#202024")
line([(682,31),(693,42)], "#c7c7cd", 2); line([(693,31),(682,42)], "#c7c7cd", 2)

# Main signal path
txt(28, 86, "Seu som, em tempo real.", 25, bold=True)
txt(28, 123, "CAPTURA  ·  PROCESSAMENTO LOCAL  ·  SAÍDA USB", 9, "#9b9ba2", True)
rr((28, 154, W-28, 225), 15, "#151518", "#252529")
steps = [(48,"IPHONE"),(218,"USB"),(353,"MICUSB AI"),(545,"VB-CABLE")]
for idx,(x,label) in enumerate(steps):
    rr((x,178,x+12,190),6,"#65d6ac" if idx<3 else "#4b4b51")
    txt(x, 198, label, 8, "#dedee2" if idx<3 else "#888890", True)
    if idx < len(steps)-1:
        line([(x+22,184),(steps[idx+1][0]-16,184)],"#45454b",2)
rr((28, 244, W-28, 610), 18, "#151518", "#252529")
txt(50, 266, "MICROFONE", 9, "#a1a1a8", True)
rr((50, 292, 80, 322), 4, "#202024")
rr((63, 298, 67, 309), 2, "#f5f5f7")
line([(59,305),(59,309),(71,309),(71,305)],"#f5f5f7",2)
txt(91, 299, "Volume", 12, "#f5f5f7", True)
txt(W-100, 300, "125%", 10, "#b8b8bf", True)
rr((50, 337, W-50, 343), 3, "#34343a")
rr((50, 337, 462, 343), 3, "#65d6ac")
rr((455, 332, 469, 348), 7, "#f5f5f7", "#e744b4", 2)
rr((50, 362, W-50, 409), 2, "#111113")
rr((63, 381, 431, 390), 3, "#34343a")
rr((63, 381, 305, 390), 3, "#20b789")
line([(326,378),(326,393)],"#f5f5f7",2)
rr((W-143, 373, W-66, 403), 5, "#252529")
txt(W-128, 382, "Testar", 10, "#f5f5f7", True)
txt(50, 428, "Sensibilidade", 12, "#f5f5f7", True)
txt(W-87, 428, "44", 12, "#f5f5f7", True)
rr((50, 461, W-50, 467), 3, "#34343a")
rr((50, 461, 340, 467), 3, "#d9d9dd")
rr((332, 455, 348, 473), 8, "#f5f5f7")
for value in range(0,101,5):
    x=50+(W-100)*value/100
    line([(x,480),(x,484 if value%10 else 487)],"#98989f",1)
    txt(x-5, 490, str(value), 7, "#a1a1a8")
txt(50, 517, "Abaixo de −55 dBFS: silenciado", 9, "#b8b8bf")
line([(50,545),(W-50,545)],"#303036",1)
txt(50, 560, "Ganho automático", 9, "#f5f5f7", True)
txt(W-100, 560, "+18 dB máx.", 9, "#b8b8bf")
txt(50, 585, "Baixe a sensibilidade se cortar sílabas; fala de TV acima do limite pode passar.", 8, "#9999a0")

txt(28, 638, "Tratamento", 17, bold=True)
txt(28, 666, "Processado localmente no PC", 10, "#9999a0")
rr((28, 696, W-28, 899), 18, "#151518", "#252529")
txt(50, 717, "Redução de ruído por IA", 12, bold=True)
txt(50, 740, "DeepFilterNet3  ·  execução local", 9, "#9a9aa1")
for box,label,sel in [((50,767,254,807),"Natural",False),((263,767,467,807),"Equilibrado",True),((476,767,680,807),"TV alta",False)]:
    rr(box,10,"#26262b" if sel else "#1e1e22", "#55555c" if sel else None)
    txt(box[0]+15,box[1]+12,label,10,"#eeeeef" if sel else "#b7b7bd",True)
line([(50,836),(W-50,836)],"#303036",1)
txt(50, 853, "Filtro de graves", 11, "#dedee2", True)
rr((W-102,849,W-52,873),12,"#65d6ac"); rr((W-79,851,W-55,871),10,"#101114")

im = im.resize((W,H), Image.Resampling.LANCZOS)
im.save(OUT / "micusb-reference.png", optimize=True)
