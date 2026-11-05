"""Folhas de sprites dos personagens e NPCs, com a paleta real de cada mapa.

Registro do mapa (ponteiro em 0x100000 + ID*4, confirmado pelo rastreio do carregador):
  palavra de cabeçalho; lista de tilesets (palavra, ponteiro Kosinski) até FFFF;
  lista de sprites (tile inicial na VRAM, ponteiro Nemesis) até FFFF.
Cada conjunto é desenhado em quadros de 2x4 tiles (16x32 px, tiles em colunas, como na tabela de
sprites do VDP). A linha de paleta vem do sprite da tabela que usa aquele tile, depois do carregamento
(mesmo patch de dump_maps.py); sem sprite visível, usa a linha 3.
Saída: assets/sprites/spr_<ponteiro>.png e sprites.csv. Uso: dump_sprites.py <estado-antes-do-carregamento>
"""
import csv
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from ps4emu import Emu, C  # noqa: E402
from pngutil import png, cram_palette  # noqa: E402
from sega_codecs import nemesis  # noqa: E402

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "sprites"
out.mkdir(parents=True, exist_ok=True)
maps = [r for r in csv.DictReader(open(root / "assets" / "maps" / "maps.csv", encoding="utf-8")) if r["status"] == "ok"]
base = Path(sys.argv[1]).read_bytes()
e = Emu()


def sprite_list(mid):
    p = struct.unpack_from(">I", rom, 0x100000 + mid * 4)[0]
    if not 0x100000 <= p < 0x200000:
        return []
    p += 2
    while struct.unpack_from(">H", rom, p)[0] != 0xFFFF:
        p += 6
    p += 2
    out_list = []
    while struct.unpack_from(">H", rom, p)[0] != 0xFFFF:
        tile, ptr = struct.unpack_from(">HI", rom, p)
        out_list.append((tile, ptr))
        p += 6
    return out_list


def sheet(path, data, pal, cols=8):
    frames = len(data) // 256  # 8 tiles por quadro
    rows = max(1, (frames + cols - 1) // cols)
    W, H = cols * 16, rows * 32
    img = bytearray(W * H * 4)
    for f in range(frames):
        for t in range(8):
            tx, ty = t // 4, t % 4  # em colunas
            tile = data[(f * 8 + t) * 32:(f * 8 + t + 1) * 32]
            for i in range(64):
                c = (tile[i // 2] >> (4 if i % 2 == 0 else 0)) & 15
                if c == 0:
                    continue
                x = (f % cols) * 16 + tx * 8 + i % 8
                y = (f // cols) * 32 + ty * 8 + i // 8
                img[(y * W + x) * 4:(y * W + x) * 4 + 4] = pal[c]
    png(path, W, H, bytes(img))


done, rows = set(), []
for r in maps:
    mid = int(r["mapa"], 16)
    sl = sprite_list(mid)
    if not sl:
        continue
    e.load_state(base)
    e.patch_rom(0x73E34, mid.to_bytes(2, "big"))
    e.press(C, 3, 20)
    e.run(240)  # espera o esmaecimento terminar, como em dump_maps.py
    v, reg, cram = e.vram(), bytes(e.mem(3)), bytes(e.mem(1))
    sat = (reg[5] & 0x7F) << 9
    used = {}
    link = 0
    for _ in range(80):
        y, size, nxt, attr, x = struct.unpack_from(">HBBHH", v, sat + link * 8)
        used[attr & 0x7FF] = (attr >> 13) & 3
        link = nxt & 0x7F
        if not link:
            break
    for tile, ptr in sl:
        if ptr in done:
            continue
        try:
            data, _ = nemesis(rom, ptr)
        except Exception:
            continue
        n_tiles = len(data) // 32
        line = next((p for t, p in used.items() if tile <= t < tile + n_tiles), 3)
        sheet(out / f"spr_{ptr:06X}.png", data, cram_palette(cram, line))
        done.add(ptr)
        rows.append({"nemesis": f"{ptr:06X}", "tiles": n_tiles, "quadros_2x4": n_tiles // 8,
                     "mapa_exemplo": r["mapa"], "linha_paleta": line,
                     "paleta_confirmada": "sim" if any(tile <= t < tile + n_tiles for t in used) else "não"})
        print(rows[-1])

with open(out / "sprites.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
