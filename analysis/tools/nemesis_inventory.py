"""Inventário dos 834 fluxos Nemesis da varredura (assets/nemesis_scan/index.csv): para cada um, a
categoria, quem o usa e onde está a extração com cores certas.

As categorias saem das tabelas de ponteiros identificadas; o que sobra é classificado pela região
do código que referencia o ponteiro. Saída: assets/nemesis_scan/inventario.csv e um resumo na tela.
"""
import csv
import struct
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
scan = {int(r["rom"], 16): r for r in csv.DictReader(open(root / "assets/nemesis_scan/index.csv"))}
cat = {}


def mark(p, c, where):
    if p in scan and p not in cat:
        cat[p] = (c, where)


def u32(a):
    return struct.unpack_from(">I", rom, a)[0]


for n in range(1, 40):
    mark(u32(0x6A4B0 + n * 4), "retrato do diálogo", "assets/portraits (export_portraits.py)")
for k in range(11):
    mark(u32(0x5D548 + k * 4), "figura da tela de status", "assets/menus/status_* (export_misc_graphics.py)")
for k in range(64):
    p = u32(0x68006 + k * 4)
    if not 0x290000 <= p < 0x2B0000:
        break
    mark(p, "retrato de loja", "assets/menus/loja_* (export_misc_graphics.py)")
for p in (0x296320, 0x296A54, 0x2971A4):
    mark(p, "veículo", "assets/menus/veiculo_* (paleta suposta)")
for k in range(32):
    mark(u32(0x6ED4 + k * 12), "cenário de batalha", "assets/battle_backgrounds")
for r in csv.DictReader(open(root / "assets/panels/panels.csv", encoding="utf-8")):
    mark(int(r["nemesis"], 16), "quadro de cena", "assets/panels (export_panels.py)")
for k in range(153):  # registro de 20 bytes: o 1º ponteiro é o corpo, os outros são partes e quadros
    mark(u32(0x27F3B8 + k * 20), "inimigo", "assets/enemies (enemy_gallery.py)")
for a in range(0x27F3B8, 0x27F3B8 + 153 * 20, 4):
    mark(u32(a), "inimigo (parte animada)", "assets/enemies, desenhada como sprite na batalha")
for base in (0x27E88A, 0x27EA66):
    offs, k = [], 0
    while not offs or base + k * 2 < base + min(offs):
        offs.append(struct.unpack_from(">H", rom, base + k * 2)[0])
        k += 1
    for o in offs:
        c = struct.unpack_from(">h", rom, base + o)[0]
        for j in range(c + 1 if 0 <= c < 40 else 0):
            mark(u32(base + o + 2 + j * 4), "efeito de batalha (técnica, skill, ataque)",
                 "assets/techniques (technique_gifs.py), animado")
for m in range(417):
    rec = u32(0x100000 + m * 4)
    if not 0x100000 <= rec < 0x200000:
        continue
    p = rec + 2
    while rom[p:p + 2] != b"\xff\xff" and p < rec + 200:
        p += 6
    p += 2
    while rom[p:p + 2] != b"\xff\xff" and p < rec + 400:
        mark(u32(p + 2), "sprite de mapa (NPC/objeto)", "assets/sprites (dump_sprites.py)")
        p += 6
mark(0x2A303A, "fonte", "assets/screens (aparece em todas as telas)")

refs = {}
for a in range(0, 0x300000 - 4, 2):
    v = u32(a)
    if v in scan:
        refs.setdefault(v, []).append(a)
REGIONS = [((0x42000, 0x44000), "abertura e título", "assets/screens/boot_* (boot_screens.py)"),
           ((0x73000, 0x74000), "abertura do jogo", "assets/screens e assets/panels"),
           ((0x5D000, 0x66000), "menus", "sem extração própria"),
           ((0x6B000, 0x7B000), "cenas e eventos", "sem extração própria"),
           ((0x0, 0x12000), "batalha (interface e efeitos)", "assets/enemies, assets/techniques")]
for p in scan:
    if p in cat:
        continue
    for (lo, hi), c, where in REGIONS:
        if any(lo <= r < hi for r in refs.get(p, [])):
            mark(p, c, where)
            break
    else:
        mark(p, "sem uso identificado" if not refs.get(p) else "outros",
             "só em tons de cinza (assets/nemesis_scan)")

rows = [{"rom": f"{p:06X}", "tiles": scan[p]["tiles"], "categoria": cat[p][0], "extração": cat[p][1],
         "referências": " ".join(f"{r:06X}" for r in refs.get(p, [])[:4])} for p in sorted(scan)]
with open(root / "assets/nemesis_scan/inventario.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
for c, n in Counter(r["categoria"] for r in rows).most_common():
    print(f"{n:4d}  {c}")
