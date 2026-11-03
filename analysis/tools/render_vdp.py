"""Converte um despejo do VDP (feito pelo app em "Exportar gráficos") em PNG.

Gera: paletas, folha com os 2048 tiles da VRAM em cada uma das 4 paletas, planos A e B
completos, sprites e o quadro como saiu na tela. Uso: render_vdp.py <pasta-do-despejo> [saida]
"""
import struct
import sys
from pathlib import Path

from pngutil import png


def swap16(b):
    """O núcleo guarda palavras em little-endian; o hardware é big-endian."""
    out = bytearray(len(b))
    out[0::2], out[1::2] = b[1::2], b[0::2]
    return bytes(out)


src = Path(sys.argv[1])
dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src / "png"
dst.mkdir(parents=True, exist_ok=True)

vram = swap16((src / "vram.bin").read_bytes())
reg = (src / "vdpreg.bin").read_bytes()
cram_raw = (src / "cram.bin").read_bytes()

# CRAM: 64 cores de 9 bits BBBGGGRRR; escala 0-7 -> 0-255.
pal = []
for i in range(64):
    v = struct.unpack_from("<H", cram_raw, i * 2)[0]
    r, g, b = v & 7, (v >> 3) & 7, (v >> 6) & 7
    pal.append(bytes((r * 255 // 7, g * 255 // 7, b * 255 // 7, 255)))
TRANSPARENT = b"\x00\x00\x00\x00"


def tile_pixels(index):
    """64 índices de cor (0-15) de um tile 8x8 de 4 bits."""
    t = vram[(index & 0x7FF) * 32:(index & 0x7FF) * 32 + 32]
    return [(t[i >> 1] >> (4 if i % 2 == 0 else 0)) & 15 for i in range(64)]


def blit(canvas, cw, x0, y0, index, palette, hflip=False, vflip=False, keep_zero=True):
    px = tile_pixels(index)
    for y in range(8):
        for x in range(8):
            c = px[(7 - y if vflip else y) * 8 + (7 - x if hflip else x)]
            if c == 0 and not keep_zero:
                continue
            o = ((y0 + y) * cw + x0 + x) * 4
            if 0 <= o < len(canvas):
                canvas[o:o + 4] = TRANSPARENT if c == 0 else pal[palette * 16 + c]


# Paletas: 4 linhas de 16 cores, 16x16 px cada.
img = bytearray(256 * 64 * 4)
for p in range(4):
    for c in range(16):
        for y in range(16):
            for x in range(16):
                o = ((p * 16 + y) * 256 + c * 16 + x) * 4
                img[o:o + 4] = pal[p * 16 + c]
png(dst / "palettes.png", 256, 64, bytes(img))

# Folha de tiles: 32 tiles por linha, 64 linhas (2048 tiles = VRAM inteira), uma por paleta.
for p in range(4):
    img = bytearray(256 * 512 * 4)
    for i in range(2048):
        blit(img, 256, (i % 32) * 8, (i // 32) * 8, i, p)
    png(dst / f"tiles_pal{p}.png", 256, 512, bytes(img))

# Planos A e B.
sizes = {0: 32, 1: 64, 3: 128}
pw, ph = sizes.get(reg[0x10] & 3, 64), sizes.get((reg[0x10] >> 4) & 3, 32)
for name, base in (("plane_a", (reg[2] & 0x38) << 10), ("plane_b", (reg[4] & 7) << 13)):
    img = bytearray(pw * 8 * ph * 8 * 4)
    for ty in range(ph):
        for tx in range(pw):
            e = struct.unpack_from(">H", vram, (base + (ty * pw + tx) * 2) & 0xFFFF)[0]
            blit(img, pw * 8, tx * 8, ty * 8, e & 0x7FF, (e >> 13) & 3, bool(e & 0x800), bool(e & 0x1000))
    png(dst / f"{name}.png", pw * 8, ph * 8, bytes(img))

# Sprites: tabela de 80 entradas de 8 bytes, encadeadas pelo campo "link".
sat = (reg[5] & 0x7F) << 9
img = bytearray(512 * 512 * 4)
link, count = 0, 0
while count < 80:
    y, size, nxt, attr, x = struct.unpack_from(">HBBHH", vram, sat + link * 8)
    sw, sh = ((size >> 2) & 3) + 1, (size & 3) + 1
    sx, sy = (x & 0x1FF), (y & 0x3FF)
    for cx in range(sw):
        for cy in range(sh):
            tx = sw - 1 - cx if attr & 0x800 else cx
            ty = sh - 1 - cy if attr & 0x1000 else cy
            blit(img, 512, sx + cx * 8, sy + cy * 8, (attr & 0x7FF) + tx * sh + ty, (attr >> 13) & 3,
                 bool(attr & 0x800), bool(attr & 0x1000), keep_zero=False)
    count += 1
    link = nxt & 0x7F
    if link == 0:
        break
png(dst / "sprites_512.png", 512, 512, bytes(img))

# Quadro final (RGB565 do frontend).
w, h = map(int, (src / "frame.txt").read_text().split())
raw = (src / "frame.raw").read_bytes()
img = bytearray(w * h * 4)
for i in range(w * h):
    v = raw[i * 2] | raw[i * 2 + 1] << 8
    img[i * 4:i * 4 + 4] = bytes((((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31, 255))
png(dst / "frame.png", w, h, bytes(img))

print(f"planos {pw}x{ph} tiles, A={(reg[2] & 0x38) << 10:04X} B={(reg[4] & 7) << 13:04X} sprites={sat:04X}, {count} sprites -> {dst}")
