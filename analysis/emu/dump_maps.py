"""Extrai todos os mapas de campo usando o próprio carregador do jogo.

A abertura do jogo novo grava o mapa inicial com `move.w #0x13,(FFEC28).w` em 0x73E32 e chama o
carregador 0x5AE98. A partir de um estado salvo logo antes disso, troca o imediato (0x73E34) por
cada ID, deixa o jogo carregar e lê o que ele montou: tiles na VRAM, paleta na CRAM, definições de
bloco em FF6000 (4x4 tiles, 32 bytes cada), camadas em FFB000 (baixo) e FFA000 (cima), dimensões
(largura-1, altura-1) em FFEC64. IDs: as 417 entradas da tabela 0x100000 (0x200 = sem mapa).
Saída: assets/maps/map_XXX.png e maps.csv.
Uso: dump_maps.py <estado-antes-do-carregamento>
"""
import csv
import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from ps4emu import Emu, C  # noqa: E402
from pngutil import png  # noqa: E402
from maplib import compose  # noqa: E402

out = Path(__file__).resolve().parent.parent / "assets" / "maps"
out.mkdir(parents=True, exist_ok=True)
for old in out.glob("map_*.png"):  # saída de uma execução anterior
    old.unlink()
base = Path(sys.argv[1]).read_bytes()
e = Emu()


rom = (Path(__file__).resolve().parent.parent / "ps4.bin").read_bytes()
table = [struct.unpack_from(">I", rom, 0x100000 + i * 4)[0] for i in range(0x684 // 4)]  # até o 1º registro
only = {int(x, 16) for x in sys.argv[2].split(",")} if len(sys.argv) > 2 else None  # teste: IDs em hex
rows, seen = [], {}
for mid, record in enumerate(table):
    if not 0x100000 <= record < 0x200000:  # 0x200 = ID sem mapa
        continue
    if only and mid not in only:
        continue
    e.load_state(base)
    e.patch_rom(0x73E34, mid.to_bytes(2, "big"))
    e.press(C, 3, 20)
    # Dois momentos: tiles e buffers são lidos no quadro em que Map_Load retorna (a abertura executa
    # 0x73E62 logo depois; mapas grandes levam mais de 80 quadros), antes de o diálogo da abertura
    # sobrescrever tiles; a paleta só fica pronta depois do esmaecimento, ~120 quadros mais tarde.
    e.trace(True)
    for _ in range(600):
        e.run(1)
        if e.executed(0x73E62):
            break
    e.trace(False)
    ram = e.ram()
    vram = e.vram()
    e.run(120)
    c = bytes(e.mem(1))
    pal_words = []
    for i in range(64):  # CRAM do núcleo (9 bits BBBGGGRRR) -> formato do hardware
        v = struct.unpack_from("<H", c, i * 2)[0]
        pal_words.append(((v >> 6 & 7) << 9) | ((v >> 3 & 7) << 5) | ((v & 7) << 1))
    if e.peek(0xFFEC28, 2) != mid:
        rows.append({"mapa": f"{mid:03X}", "registro": f"{record:06X}", "status": "não carregou"})
        continue
    w, h = ram[0xEC64] + 1, ram[0xEC65] + 1
    stride = 32 if w * h <= 1024 else w
    size = stride * h
    lower, upper = ram[0xB000:0xB000 + size], ram[0xA000:0xA000 + size]
    blocks = ram[0x6000:0xA000]
    key = hashlib.sha1(lower + upper + blocks[:4096]).hexdigest()
    if key in seen:
        rows.append({"mapa": f"{mid:03X}", "registro": f"{record:06X}", "status": f"igual a {seen[key]}", "largura": w, "altura": h})
        continue
    seen[key] = f"{mid:03X}"
    if size > 0x1000:  # camada maior que a janela de 4 KB: o mapa é carregado em partes ao andar
        rows.append({"mapa": f"{mid:03X}", "registro": f"{record:06X}", "status": "grande: carregado em partes",
                     "largura": w, "altura": h})
        continue
    W, H, img = compose(vram, pal_words, blocks, (lower, upper), w, h, stride)
    png(out / f"map_{mid:03X}.png", W, H, img)
    rows.append({"mapa": f"{mid:03X}", "registro": f"{record:06X}", "status": "ok", "largura": w, "altura": h})
    print(rows[-1])

with open(out / "maps.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=["mapa", "registro", "status", "largura", "altura"])
    wr.writeheader()
    wr.writerows(rows)
print(sum(r["status"] == "ok" for r in rows), "mapas distintos")
