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

out = Path(__file__).resolve().parent.parent / "assets" / "maps"
out.mkdir(parents=True, exist_ok=True)
for old in out.glob("map_*.png"):  # saída de uma execução anterior
    old.unlink()
base = Path(sys.argv[1]).read_bytes()
e = Emu()


def compose(vram, palette_words, blocks, layers, w, h, stride):
    """palette_words: 64 cores no formato do hardware (0000BBB0GGG0RRR0)."""
    pal = []
    for c in palette_words:
        r, g, b = (c >> 1) & 7, (c >> 5) & 7, (c >> 9) & 7
        pal.append(bytes((r * 255 // 7, g * 255 // 7, b * 255 // 7, 255)))
    W, H = w * 32, h * 32
    img = bytearray(W * H * 4)
    cache = {}

    def tile_rows(ent):
        """8 linhas RGBA de um tile (com paleta e espelhamento) e a máscara de cor 0 por linha."""
        key = ent & 0x7FFF
        if key not in cache:
            t, p = (ent & 0x7FF) * 32, (ent >> 13) & 3
            hf, vf = ent & 0x800, ent & 0x1000
            rows = []
            for y in range(8):
                src = vram[t + (7 - y if vf else y) * 4:][:4]
                idx = [(src[(7 - x if hf else x) >> 1] >> (0 if (7 - x if hf else x) & 1 else 4)) & 15
                       for x in range(8)]
                rows.append((b"".join(pal[p * 16 + c] for c in idx), idx))
            cache[key] = rows
        return cache[key]

    for layer_index, layout in enumerate(layers):
        for by in range(h):
            for bx in range(w):
                b = layout[by * stride + bx]
                if b * 32 + 32 > len(blocks):
                    continue
                for k, ent in enumerate(struct.unpack_from(">16H", blocks, b * 32)):
                    ox, oy = bx * 32 + (k % 4) * 8, by * 32 + (k // 4) * 8
                    for y, (rgba, idx) in enumerate(tile_rows(ent)):
                        o = ((oy + y) * W + ox) * 4
                        if layer_index == 0:
                            img[o:o + 32] = rgba
                        else:  # camada de cima: cor 0 é transparente
                            for x, c in enumerate(idx):
                                if c:
                                    img[o + x * 4:o + x * 4 + 4] = rgba[x * 4:x * 4 + 4]
    return W, H, bytes(img)


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
    # Dois momentos: aos ~80 quadros os tiles do mapa já estão na VRAM e o diálogo da abertura ainda
    # não abriu (ele sobrescreve tiles); a paleta só fica pronta depois do esmaecimento (~180 quadros).
    e.run(60)
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
