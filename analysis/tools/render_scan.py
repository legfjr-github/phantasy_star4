"""Gera PNG para cada fluxo de assets/nemesis_scan.

Sem despejo: tons de cinza. Com despejo (render_scan.py <pasta-do-despejo>): os fluxos cujos tiles
estão na VRAM daquela cena usam a linha de paleta que os planos/sprites aplicam a esses tiles.
"""
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pngutil import GRAY, cram_palette, tiles_png  # noqa: E402

here = Path(__file__).resolve().parent.parent
scan = here / "assets" / "nemesis_scan"

tile_line = {}
palettes = None
if len(sys.argv) > 1:
    d = Path(sys.argv[1])
    raw = (d / "vram.bin").read_bytes()
    vram = bytes(b for i in range(0, len(raw), 2) for b in (raw[i + 1], raw[i]))
    reg = (d / "vdpreg.bin").read_bytes()
    cram = (d / "cram.bin").read_bytes()
    palettes = [cram_palette(cram, line) for line in range(4)]
    index_line = Counter()
    sizes = {0: 32, 1: 64, 3: 128}
    pw, ph = sizes.get(reg[0x10] & 3, 64), sizes.get((reg[0x10] >> 4) & 3, 32)
    for base in ((reg[2] & 0x38) << 10, (reg[4] & 7) << 13):
        for i in range(pw * ph):
            e = struct.unpack_from(">H", vram, (base + i * 2) & 0xFFFF)[0]
            index_line[(e & 0x7FF, (e >> 13) & 3)] += 1
    sat = (reg[5] & 0x7F) << 9
    for s in range(80):
        _, size, _, attr, _ = struct.unpack_from(">HBBHH", vram, sat + s * 8)
        n = (((size >> 2) & 3) + 1) * ((size & 3) + 1)
        for k in range(n):
            index_line[((attr & 0x7FF) + k, (attr >> 13) & 3)] += 1
    by_index = {}
    for (idx, line), c in index_line.items():
        if c > by_index.get(idx, (0, -1))[0]:
            by_index[idx] = (c, line)
    for idx in range(2048):
        t = vram[idx * 32:idx * 32 + 32]
        if t != bytes(32) and idx in by_index:
            tile_line.setdefault(t, by_index[idx][1])

colored = 0
for f in sorted(scan.glob("nem_*.bin")):
    data = f.read_bytes()
    pal = GRAY
    if tile_line:
        votes = Counter(tile_line[data[i:i + 32]] for i in range(0, len(data), 32) if data[i:i + 32] in tile_line)
        if votes:
            pal = palettes[votes.most_common(1)[0][0]]
            colored += 1
    tiles_png(f.with_suffix(".png"), data, pal)
print(f"{len(list(scan.glob('nem_*.png')))} PNG, {colored} com a paleta da cena")
