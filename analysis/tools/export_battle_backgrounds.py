"""Cenários de batalha (rotina 0x6BFC, chamada na montagem da batalha).

Escolha do cenário: batalha fixa (FFECFC >= 0) -> tabela 0x6C8C[formação]; mapa diferente de 0 ->
tabela 0x6CA8[mapa] (FF = sem encontro); em Motavia (mapa 0) -> o tipo de terreno em FFECEF.
O número 4 vira 5 se a flag 0x9E estiver ligada.
Cada cenário é um registro de 12 bytes em 0x6ED4: tiles Nemesis (VRAM 0), mapa Enigma (para FF9000,
64x24 células) e paleta (13 cores para a linha 0, a partir da cor 1). São 32 cenários.
Saída: assets/battle_backgrounds/bg_<n>.png e backgrounds.csv (quais mapas e batalhas fixas usam cada um).
"""
import csv
import struct
from pathlib import Path

from pngutil import png
from sega_codecs import enigma, nemesis

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "battle_backgrounds"
out.mkdir(parents=True, exist_ok=True)
W_CELLS = 64

by_map = {}
for m in range(417):
    by_map.setdefault(rom[0x6CA8 + m], []).append(f"{m:03X}")
by_fixed = {}
for n in range(27):
    by_fixed.setdefault(rom[0x6C8C + n], []).append(str(n))

rows = []
for k in range(32):
    nem, eni, palp = struct.unpack_from(">III", rom, 0x6ED4 + k * 12)
    tiles, _ = nemesis(rom, nem)
    vram = bytearray(0x10000)
    vram[:len(tiles)] = tiles
    words_raw, _ = enigma(rom, eni, 0)
    words = struct.unpack_from(f">{len(words_raw) // 2}H", words_raw)
    cols = [bytes((0, 0, 0, 255))]
    for c in struct.unpack_from(">13H", rom, palp):
        r, g, b = (c >> 1) & 7, (c >> 5) & 7, (c >> 9) & 7
        cols.append(bytes((r * 255 // 7, g * 255 // 7, b * 255 // 7, 255)))
    cols += [bytes((0, 0, 0, 255))] * 2
    h_cells = len(words) // W_CELLS
    W, H = W_CELLS * 8, h_cells * 8
    img = bytearray(W * H * 4)
    for i, ent in enumerate(words[:W_CELLS * h_cells]):
        cx, cy = i % W_CELLS, i // W_CELLS
        t, hf, vf = ent & 0x7FF, ent & 0x800, ent & 0x1000
        for y in range(8):
            row = vram[t * 32 + (7 - y if vf else y) * 4:][:4]
            for x in range(8):
                sx = 7 - x if hf else x
                c = (row[sx >> 1] >> (0 if sx & 1 else 4)) & 15
                o = ((cy * 8 + y) * W + cx * 8 + x) * 4
                img[o:o + 4] = cols[c]
    png(out / f"bg_{k:02d}.png", W, H, bytes(img))
    rows.append({"cenario": k, "nemesis": f"{nem:06X}", "enigma": f"{eni:06X}", "paleta": f"{palp:06X}",
                 "mapas": " ".join(by_map.get(k, [])), "batalhas_fixas": " ".join(by_fixed.get(k, []))})
with open(out / "backgrounds.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
print(len(rows), "cenários")
