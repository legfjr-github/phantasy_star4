"""Exploração automática: anda ao acaso a partir de um estado até chegar a um mapa-alvo e, opcionalmente,
até a primeira batalha (detectada pela execução de Battle_LoadEnemy, 0x7F5E).

Uso: explore.py <estado-inicial> <mapa-alvo-hex> <saida.state> [--batalha] [quadros-max]
Fecha diálogos com B, anda em rajadas longas e volta ao último estado bom se ficar preso.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ps4emu import Emu, B, C, UP, DOWN, LEFT, RIGHT  # noqa: E402

start, target, out = Path(sys.argv[1]).read_bytes(), int(sys.argv[2], 16), Path(sys.argv[3])
want_battle = "--batalha" in sys.argv
limit = int(next((a for a in sys.argv[4:] if a.isdigit()), "400000"))
e = Emu()
e.load_state(start)
rng = random.Random(11)
path, frames = [e.peek(0xFFEC28, 2)], 0
seen_states = {}  # primeiro estado em cada mapa novo, gravado como map_XXX_entry.state ao lado da saída
if want_battle:
    e.trace(True)
while frames < limit:
    d = rng.choice((UP, DOWN, LEFT, RIGHT))
    n = rng.randint(30, 160)
    e.run(n, d)
    e.press(B, 3, 10)
    frames += n + 13
    m = e.peek(0xFFEC28, 2)
    if m != path[-1]:
        path.append(m)
        print(f"quadro {frames}: mapa {m:#x}")
        if m not in seen_states:
            seen_states[m] = e.save_state()
            (out.parent / f"map_{m:03X}_entry.state").write_bytes(seen_states[m])
    if m == target and not want_battle:
        break
    if want_battle and m == target and frames % 600 < 200:
        marks = e.marks()
        if any(marks[a] & 2 for a in range(0x7F5E, 0x7F70)):
            print(f"batalha no quadro {frames}")
            for _ in range(5):
                e.run(30)
            break
out.write_bytes(e.save_state())
print("caminho:", " -> ".join(f"{m:#x}" for m in path), "| quadros:", frames)
