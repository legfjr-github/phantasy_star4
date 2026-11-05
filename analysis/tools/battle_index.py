"""Índice dos inimigos vistos nas batalhas do emulador (emu/battle_session.py).

Para cada inimigo lido da tabela 0x2816BC durante uma batalha, lista as capturas de tela (inimigos com a
paleta real) e grava a paleta daquela batalha em PNG. Saída: assets/battles/enemies_seen.csv e
pal_<batalha>.png. Os gráficos de inimigo vêm do carregador 0x7C56 (tabela 0x27F3B8, 153 registros de
20 bytes: ponteiro Nemesis dos pedaços, tamanho/ID e ponteiros de animação; quadros montados por 0x10FCE),
por isso a imagem confiável é a da própria tela.
"""
import csv
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pngutil import png, cram_palette  # noqa: E402

root = Path(__file__).resolve().parent.parent
bat = root / "assets" / "battles"
enemies = {int(r["id"]): r["nome"] for r in csv.DictReader(open(root / "assets" / "data" / "enemies.csv", encoding="utf-8"))}
seen = {}
for r in csv.DictReader(open(bat / "battles.csv", encoding="utf-8")):
    tag = f"{r['mapa']}_{r['batalha']}"
    cram = (bat / f"cram_{tag}.bin").read_bytes()
    img = bytearray(16 * 4 * 16 * 16 * 4)
    for line in range(4):
        for c, rgba in enumerate(cram_palette(cram, line)):
            for y in range(16):
                for x in range(16):
                    o = ((line * 16 + y) * 256 + c * 16 + x) * 4
                    img[o:o + 4] = rgba
    png(bat / f"pal_{tag}.png", 256, 64, bytes(img[:256 * 64 * 4]))
    for i in r["inimigos"].split():
        i = int(i)
        if i < 153:  # IDs acima são entradas lidas de outras tabelas no mesmo intervalo
            seen.setdefault(i, []).append(tag)

with open(bat / "enemies_seen.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "nome", "batalhas (battle_<mapa>_<n>.png / pal_<...>.png)"])
    for i in sorted(seen):
        w.writerow([i, enemies.get(i, "?"), " ".join(seen[i])])
print(len(seen), "inimigos distintos vistos em batalha")
