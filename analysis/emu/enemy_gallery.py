"""Galeria de todos os inimigos: força cada ID numa batalha e fotografa.

Como funciona:
1. battlelib.setup entra numa masmorra com encontros e anda até uma batalha começar, ficando com o
   estado e o passo que levaram a ela (repetir o passo repete o encontro).
2. Para cada ID, troca na ROM carregada a leitura da formação (0x7EF0..0x7F14) para que ela venha de
   um registro montado em espaço livre (0x2F5000): `lea (0x2F5000).l,A0` em 0x7F00 e `bra.b 0x7F14` em
   0x7F06. O registro é o de uma formação comum de 1 inimigo (cabeçalho 10 00 08 80, 1 inimigo,
   máscara 01 00, par ID/X, FF). Formações fixas (chefes, 0x284F7C) entram com os próprios bytes.
3. Repete o passo, espera a batalha montar e grava a tela, o inimigo recortado e a CRAM.

Na batalha não há sprites: inimigos, grupo e janelas ficam no plano A (0xC000) e o cenário no B.
Os tiles do inimigo vêm depois dos do grupo (no estado usado, só o Chaz, tiles 390-406) e antes da
fonte e das janelas (1664 em diante), então o recorte pega as células do plano A com tile 407-1663.
Só os IDs 0-152 são inimigos (a tabela de gráficos 0x27F3B8 tem 153 entradas); depois deles a lista
de nomes segue com nomes de ataques.

Saída: assets/enemies/enemy_<id>.png (tela), enemy_<id>_spr.png (só o inimigo, recortado),
fixed_<n>.png e enemies_gallery.csv. Uso: enemy_gallery.py <preload.state> [primeiro último]
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import battlelib as lib  # noqa: E402
from pngutil import png  # noqa: E402
from sega_codecs import kosinski  # noqa: E402

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "enemies"
out.mkdir(parents=True, exist_ok=True)
first, last = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 152)
FREE = 0x2F5000

names = [r["nome"] for r in csv.DictReader(open(root / "assets" / "data" / "enemies.csv", encoding="utf-8"))]
e, state, step = lib.setup(Path(sys.argv[1]).read_bytes())


def battle_with(record, tag):
    e.patch_rom(FREE, record + b"\xff" * (32 - len(record)))
    e.load_state(state)
    e.trace(True)
    lib.do_step(e, step)
    if not e.executed(0x7F5E):
        return "sem batalha"
    e.run(150)
    ok = not e.executed(0x200)
    e.screenshot(out / f"{tag}.png")
    (out / f"{tag}_cram.bin").write_bytes(bytes(e.mem(1)))
    W, H, img, cells = lib.plane_a(e, lambda t, cy: 407 <= t < 1664)
    if cells:
        png(out / f"{tag}_spr.png", *lib.crop(W, img, cells))
    return "ok" if ok else "travou"


e.patch_rom(0x7F00, bytes.fromhex("41F9") + FREE.to_bytes(4, "big"))
e.patch_rom(0x7F06, bytes.fromhex("600C"))
rows = []
for i in range(first, last + 1):
    st = battle_with(bytes.fromhex("1000088001 0100") + bytes((i, 0x14, 0xFF)), f"enemy_{i:03d}")
    rows.append({"tipo": "inimigo", "id": i, "nome": names[i] if i < len(names) else "", "resultado": st})
    print(rows[-1])
fixed, _ = kosinski(rom, 0x284F7C)
for n, rec in enumerate(fixed.split(b"\xff")):
    if len(rec) < 7:
        continue
    st = battle_with(rec + b"\xff", f"fixed_{n:02d}")
    ids = rec[7::2]
    rows.append({"tipo": "formação fixa", "id": n, "nome": " | ".join(names[i] if i < len(names) else str(i)
                                                                    for i in ids), "resultado": st})
    print(rows[-1])
with open(out / "enemies_gallery.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
