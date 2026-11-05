"""Sessão de batalhas naturais: carrega masmorras pela abertura (mesmo patch de dump_maps.py), anda ao
acaso até um encontro (Battle_LoadEnemy, 0x7F5E, executa), registra o que a batalha leu da ROM e luta
apertando C até acabar.

Por batalha: inimigos (registros lidos de 0x2816BC), fluxos gráficos lidos na ROM ao montar a batalha,
e a CRAM com a batalha na tela (paleta dos inimigos). Tudo vai para assets/battles/ e a cobertura de
execução se soma a export/exec_marks.bin.
Uso: battle_session.py <estado-antes-do-carregamento> [batalhas-por-mapa]
"""
import csv
import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ps4emu import Emu, C, B, UP, DOWN, LEFT, RIGHT  # noqa: E402

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "battles"
out.mkdir(parents=True, exist_ok=True)
base = Path(sys.argv[1]).read_bytes()
per_map = int(sys.argv[2]) if len(sys.argv) > 2 else 3
ENEMY_BASE, ENEMY_SIZE, N_ENEMIES = 0x2816BC, 48, 266

zone_of_map = rom[0x8050:0x8050 + 417]
maps = [m for m in range(417) if 1 < zone_of_map[m] < 0xFF
        and 0x100000 <= struct.unpack_from(">I", rom, 0x100000 + m * 4)[0] < 0x200000]

e = Emu()
rng = random.Random(5)
coverage = bytearray(0x400000)
rows = []


def read_runs(marks, lo, hi, min_len):
    runs, a = [], lo
    while a < hi:
        if marks[a] & 1 and not marks[a] & 2:
            b = a
            while b < hi and marks[b] & 1 and not marks[b] & 2:
                b += 1
            if b - a >= min_len:
                runs.append((a, b - a))
            a = b
        else:
            a += 1
    return runs


for mid in maps:
    e.load_state(base)
    e.patch_rom(0x73E34, mid.to_bytes(2, "big"))
    e.press(C, 3, 20)
    for _ in range(40):
        e.press(B, 3, 15)
    battles = 0
    walked = 0
    while battles < per_map and walked < 40000:
        e.trace(True)
        while walked < 40000 and not e.executed(0x7F5E):
            e.run(rng.randint(20, 80), rng.choice((UP, DOWN, LEFT, RIGHT)))
            e.press(B, 3, 8)
            walked += 100
        if not e.executed(0x7F5E):
            break
        e.run(150)  # gráficos e paleta da batalha montados
        marks = e.marks()
        enemy_ids = sorted({(a - ENEMY_BASE) // ENEMY_SIZE for a, n in read_runs(marks, ENEMY_BASE,
                            ENEMY_BASE + N_ENEMIES * ENEMY_SIZE, 2)})
        gfx = [f"{a:06X}+{n}" for a, n in read_runs(marks, 0x080000, 0x300000, 256)]
        cram = bytes(e.mem(1))
        tag = f"{mid:03X}_{battles}"
        (out / f"cram_{tag}.bin").write_bytes(cram)
        e.screenshot(out / f"battle_{tag}.png")
        # luta: C até o modo de campo voltar (FFEC28 volta a ser o mapa e Battle_GiveRewards ou fuga)
        e.trace(True, clear=False)
        for _ in range(300):
            e.press(C, 3, 20)
            if e.peek(0xFFEC28, 2) == mid and e.peek(0xFFEC20, 2) == 0xC:
                break
        won = e.executed(0x300A)
        marks = e.marks()
        for i, b in enumerate(marks):
            if b:
                coverage[i] |= b
        rows.append({"mapa": f"{mid:03X}", "zona": zone_of_map[mid], "batalha": battles,
                     "inimigos": " ".join(str(i) for i in enemy_ids), "graficos_lidos": " ".join(gfx),
                     "vitoria": "sim" if won else "não", "travou": "sim" if e.executed(0x200) else "não"})
        print(rows[-1])
        battles += 1
        if e.executed(0x200):
            break

old = root / "export" / "exec_marks.bin"
prev = old.read_bytes() if old.exists() else bytes(len(coverage))
old.write_bytes(bytes(a | b for a, b in zip(prev, coverage)))
with open(out / "battles.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
print(len(rows), "batalhas;", "executadas no total:", sum(1 for b in old.read_bytes() if b & 2))
