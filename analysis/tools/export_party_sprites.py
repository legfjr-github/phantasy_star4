"""Sprites de campo dos 11 personagens jogáveis.

Tabela em 0x5E732: 11 ponteiros (um por personagem, na ordem dos IDs: Chaz, Alys, Hahn, Rune, Gryz,
Rika, Demi, Wren, Raja, Kyra, Seth) para folhas sem compressão de 0x900 bytes em 0x290000. Cada folha
tem 72 tiles = 9 quadros de 2x4 tiles (16x32 px, tiles em colunas, como na tabela de sprites do VDP);
o jogo copia só o quadro da vez para a VRAM. A paleta (linha 2 da CRAM) vem logo depois, em 0x296300.
Achado procurando na ROM os tiles que estavam na VRAM com o grupo andando no campo.
Saída: assets/party/field_<id>_<nome>.png (9 quadros lado a lado, ampliados 2x também em _x2).
"""
import struct
from pathlib import Path

from pngutil import png

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "party"
out.mkdir(parents=True, exist_ok=True)
NAMES = ["Chaz", "Alys", "Hahn", "Rune", "Gryz", "Rika", "Demi", "Wren", "Raja", "Kyra", "Seth"]
TABLE, PAL = 0x5E732, 0x296300

pal = []
for c in struct.unpack_from(">16H", rom, PAL):
    r, g, b = (c >> 1) & 7, (c >> 5) & 7, (c >> 9) & 7
    pal.append(bytes((r * 255 // 7, g * 255 // 7, b * 255 // 7, 255)))

for cid, name in enumerate(NAMES):
    sheet = struct.unpack_from(">I", rom, TABLE + cid * 4)[0]
    frames = 9
    W, H = frames * 16, 32
    img = bytearray(W * H * 4)
    for f in range(frames):
        for k in range(8):  # 2 colunas x 4 linhas, em colunas
            tx, ty = k // 4, k % 4
            t = rom[sheet + (f * 8 + k) * 32:][:32]
            for y in range(8):
                for x in range(8):
                    c = (t[y * 4 + x // 2] >> (0 if x & 1 else 4)) & 15
                    if c:
                        o = ((ty * 8 + y) * W + f * 16 + tx * 8 + x) * 4
                        img[o:o + 4] = pal[c]
    png(out / f"field_{cid:02d}_{name}.png", W, H, bytes(img))
    big = bytearray(W * 2 * H * 2 * 4)
    for y in range(H * 2):
        for x in range(W * 2):
            s = ((y // 2) * W + x // 2) * 4
            big[(y * W * 2 + x) * 4:(y * W * 2 + x) * 4 + 4] = img[s:s + 4]
    png(out / f"field_{cid:02d}_{name}_x2.png", W * 2, H * 2, bytes(big))
    print(name, hex(sheet))
