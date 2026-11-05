"""Retratos da caixa de diálogo (controle de texto F4 n, tratado em 0x69C42).

A tabela 0x6A4B0 tem um ponteiro Nemesis por retrato (o 0 é vazio; 39 retratos). O tratador
descomprime o retrato no tile 0x55C da VRAM e desenha 6x6 células com o mapa fixo 0x2A2B36
(C55C, C55D, ... em linhas: linha de paleta 2 e prioridade). A linha 2 da CRAM é a paleta dos
personagens, a mesma dos sprites de campo (0x296300).
Saída: assets/portraits/face_<n>.png (48x48) e _x3 (ampliado).
"""
import struct
from pathlib import Path

from pngutil import png
from sega_codecs import nemesis

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "portraits"
out.mkdir(parents=True, exist_ok=True)

pal = []
for c in struct.unpack_from(">16H", rom, 0x296300):
    r, g, b = (c >> 1) & 7, (c >> 5) & 7, (c >> 9) & 7
    pal.append(bytes((r * 255 // 7, g * 255 // 7, b * 255 // 7, 255)))
layout = struct.unpack_from(">36H", rom, 0x2A2B36)

n = 1
while True:
    ptr = struct.unpack_from(">I", rom, 0x6A4B0 + n * 4)[0]
    if not 0x290000 <= ptr < 0x2B0000:
        break
    tiles, _ = nemesis(rom, ptr)
    img = bytearray(48 * 48 * 4)
    for i, ent in enumerate(layout):
        t = (ent & 0x7FF) - 0x55C
        cx, cy = i % 6, i // 6
        for y in range(8):
            for x in range(8):
                c = (tiles[t * 32 + y * 4 + x // 2] >> (0 if x & 1 else 4)) & 15
                o = ((cy * 8 + y) * 48 + cx * 8 + x) * 4
                img[o:o + 4] = pal[c]
    png(out / f"face_{n:02d}.png", 48, 48, bytes(img))
    big = bytearray(144 * 144 * 4)
    for y in range(144):
        for x in range(144):
            s = ((y // 3) * 48 + x // 3) * 4
            big[(y * 144 + x) * 4:(y * 144 + x) * 4 + 4] = img[s:s + 4]
    png(out / f"face_{n:02d}_x3.png", 144, 144, bytes(big))
    n += 1
print(n - 1, "retratos")
