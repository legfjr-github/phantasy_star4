"""Gráficos de menu e de campo achados pelas tabelas de ponteiros que sobraram na varredura Nemesis.

- Figuras da tela de status (rotina 0x5CE60): tabela 0x5D548 com um Nemesis por personagem,
  descomprimido no tile 0x580, e tabela 0x5D574 com o mapa de 10x10 palavras (200 bytes por
  personagem; linha de paleta 2, a dos personagens, 0x296300).
- Retratos das lojas: tabela 0x68006, um Nemesis de 6x6 tiles por loja (em linhas, como os retratos
  do diálogo), paleta 0x296300. Saem só os distintos.
- Veículos (tabela 0x51AA6, carregada em 0x51A8C pela flag FFF43C): três folhas Nemesis em quadros
  de 2x4 tiles em colunas. A paleta usada aqui é a dos personagens, que não foi confirmada para eles.
Saída: assets/menus/status_<n>.png, assets/menus/loja_<ptr>.png, assets/menus/veiculo_<n>.png.
"""
import struct
from pathlib import Path

from pngutil import png
from sega_codecs import nemesis

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "menus"
out.mkdir(parents=True, exist_ok=True)
NAMES = ["Chaz", "Alys", "Hahn", "Rune", "Gryz", "Rika", "Demi", "Wren", "Raja", "Kyra", "Seth"]
PAL = []
for c in struct.unpack_from(">16H", rom, 0x296300):
    PAL.append(bytes((((c >> 1) & 7) * 255 // 7, ((c >> 5) & 7) * 255 // 7, ((c >> 9) & 7) * 255 // 7, 255)))


def draw(tiles, cells, w, h, transparent=False):
    """cells: lista (índice do tile, hflip, vflip) em linhas de w."""
    img = bytearray(w * 8 * h * 8 * 4)
    for i, (t, hf, vf) in enumerate(cells):
        cx, cy = i % w, i // w
        for y in range(8):
            for x in range(8):
                sx, sy = (7 - x if hf else x), (7 - y if vf else y)
                if not 0 <= t < len(tiles) // 32:
                    continue
                c = (tiles[t * 32 + sy * 4 + sx // 2] >> (0 if sx & 1 else 4)) & 15
                if c or not transparent:
                    o = ((cy * 8 + y) * w * 8 + cx * 8 + x) * 4
                    img[o:o + 4] = PAL[c]
    return w * 8, h * 8, bytes(img)


for k in range(11):
    tiles, _ = nemesis(rom, struct.unpack_from(">I", rom, 0x5D548 + k * 4)[0])
    words = struct.unpack_from(">100H", rom, struct.unpack_from(">I", rom, 0x5D574 + k * 4)[0])
    cells = [((v & 0x7FF) - 0x580, v & 0x800, v & 0x1000) for v in words]
    png(out / f"status_{k:02d}_{NAMES[k]}.png", *draw(tiles, cells, 10, 10))

seen = []
for k in range(64):
    p = struct.unpack_from(">I", rom, 0x68006 + k * 4)[0]
    if not 0x290000 <= p < 0x2B0000:
        break
    if p in seen:
        continue
    seen.append(p)
    tiles, _ = nemesis(rom, p)
    png(out / f"loja_{p:06X}.png", *draw(tiles, [(i, 0, 0) for i in range(36)], 6, 6))

for k, p in enumerate((0x296320, 0x296A54, 0x2971A4)):
    tiles, _ = nemesis(rom, p)
    n = len(tiles) // 32
    frames = (n + 7) // 8
    cells = []
    for row in range(4):
        for f in range(frames):
            for col in range(2):
                cells.append((f * 8 + col * 4 + row, 0, 0))
    png(out / f"veiculo_{k}.png", *draw(tiles, cells, frames * 2, 4, transparent=True))
print("status 11, lojas", len(seen), ", veículos 3")
