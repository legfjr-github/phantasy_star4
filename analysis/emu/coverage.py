"""Cobertura de execução real: roda o jogo com rastreio e grava export/exec_marks.bin
(1 byte por endereço da ROM: bit 0 = lido como dado, bit 1 = executado).

Começa no menu de título (depois da verificação de checksum do boot, que lê a ROM inteira) e passa
por: abertura até a primeira cidade, jogo com entradas aleatórias na cidade e no campo (batalhas,
menus, diálogos). As marcas se acumulam entre as etapas.
Uso: coverage.py <estado-do-titulo> <estado-da-cidade> [quadros-por-etapa]
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ps4emu import Emu, START, C, A, B, UP, DOWN, LEFT, RIGHT  # noqa: E402

title, town = Path(sys.argv[1]).read_bytes(), Path(sys.argv[2]).read_bytes()
frames = int(sys.argv[3]) if len(sys.argv) > 3 else 60000
e = Emu()
rng = random.Random(4)
e.trace(True)

# 1) título -> jogo novo -> abertura
e.load_state(title)
e.press(START)
e.run(180)
for _ in range(400):
    e.press(C, 3, 20)

# 2) jogo aleatório a partir da cidade: anda em rajadas, aperta botões, às vezes abre o menu
for seed in range(3):
    e.load_state(town)
    done = 0
    while done < frames:
        d = rng.choice((UP, DOWN, LEFT, RIGHT))
        n = rng.randint(10, 90)
        e.run(n, d)
        b = rng.choice((C, C, C, A, B, START, 0))
        e.press(b, 3, rng.randint(5, 30))
        done += n + 30
    print("etapa", seed, "ok; mapa atual", e.peek(0xFFEC28, 2))

e.trace(False, clear=False)
m = e.marks()
out = Path(__file__).resolve().parent.parent / "export" / "exec_marks.bin"
out.write_bytes(m)
print("executados:", sum(1 for b in m if b & 2), "lidos:", sum(1 for b in m if b & 1))
