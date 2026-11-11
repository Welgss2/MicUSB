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
rr((28, 244, W-28, 554), 18, "#151518", "#252529")
txt(50, 267, "NÍVEL DE ENTRADA", 9, "#a1a1a8", True)
txt(50, 290, "Microfone do iPhone", 17, bold=True)
rr((50, 327, W-50, 372), 11, "#202024")
txt(66, 339, "Automático · matriz de voz do iPhone", 11, "#dedee2")
txt(W-92, 339, "⌄", 13, "#9b9ba2")
txt(50, 394, "Ganho de voz", 11, "#dadade", True)
txt(W-91, 394, "+3 dB", 11, "#b8b8bf", True)
rr((50, 421, W-50, 427), 3, "#34343a")
rr((50, 421, 264, 427), 3, "#65d6ac")
rr((253, 416, 265, 432), 6, "#f5f5f7")
txt(50, 446, "Nível do microfone", 10, "#aaaab2")
txt(W-130, 446, "−24 dBFS", 10, "#dedee2", True)
rr((50, 473, W-50, 516), 10, "#202024")
for x,h in [(63,8),(72,14),(81,19),(90,25),(99,15),(108,22),(117,31),(126,18),(135,27),(144,34),(153,20),(162,12),(171,18),(180,27),(189,15),(198,23),(207,13),(216,18),(225,9)]:
    rr((x,495-h/2,x+4,495+h/2),2,"#65d6ac" if x<180 else "#414147")
rr((W-143, 476, W-66, 513), 9, "#e8e8eb")
txt(W-128, 486, "Testar", 10, "#151518", True)
txt(50, 527, "Fale normalmente. O nível atualiza sem gravar sua voz.", 9, "#96969e")

txt(28, 583, "Tratamento", 17, bold=True)
txt(28, 612, "Processado localmente no PC", 10, "#9999a0")
rr((28, 642, W-28, 888), 18, "#151518", "#252529")
txt(50, 663, "Redução de ruído por IA", 12, bold=True)
txt(50, 686, "DeepFilterNet3  ·  execução local", 9, "#9a9aa1")
for box,label,sel in [((50,713,254,753),"Natural",False),((263,713,467,753),"Equilibrado",True),((476,713,680,753),"TV alta",False)]:
    rr(box,10,"#26262b" if sel else "#1e1e22", "#55555c" if sel else None)
    txt(box[0]+15,box[1]+12,label,10,"#eeeeef" if sel else "#b7b7bd",True)
txt(50, 777, "Ganho", 10, "#dadade", True); txt(W-93,777,"+3 dB",10,"#b8b8bf",True)
rr((50,802,W-50,808),3,"#34343a"); rr((50,802,307,808),3,"#65d6ac"); rr((296,797,308,813),6,"#f5f5f7")
line([(50,836),(W-50,836)],"#303036",1)
txt(50, 853, "Filtro de graves", 11, "#dedee2", True)
rr((W-102,849,W-52,873),12,"#65d6ac"); rr((W-79,851,W-55,871),10,"#101114")
txt(28, 907, "A fala da TV pode ser reduzida; fala sobreposta pode exigir ajuste de posição.", 9, "#919198")

im = im.resize((W,H), Image.Resampling.LANCZOS)
im.save(OUT / "micusb-reference.png", optimize=True)
