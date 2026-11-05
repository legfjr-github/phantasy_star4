"""Sprites de batalha (de costas) dos 11 personagens.

Parte do mesmo encontro de enemy_gallery.py (estado e passo que levam a uma batalha). Antes do passo,
põe 5 personagens no grupo (FFF40A) copiando a ficha do Chaz (FFF500, 0x80 bytes) para os que estão
zerados, e deixa a batalha montar. O grupo fica no plano A, linhas 15-20; cada membro é recortado das
células com tile diferente de 0 e abaixo da fonte (1664). Na tela, a ordem das posições da esquerda
para a direita é 4º, 2º, 1º, 3º e 5º membro.
Saída: assets/party/battle_<id>_<nome>.png e battle_grupo<n>.png (tela inteira).
Uso: party_battle.py <preload.state>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import battlelib as lib  # noqa: E402
from pngutil import png  # noqa: E402

root = Path(__file__).resolve().parent.parent
out = root / "assets" / "party"
out.mkdir(parents=True, exist_ok=True)
NAMES = ["Chaz", "Alys", "Hahn", "Rune", "Gryz", "Rika", "Demi", "Wren", "Raja", "Kyra", "Seth"]
SCREEN_ORDER = [3, 1, 0, 2, 4]  # índice no grupo de quem está em cada posição, da esquerda para a direita

e, state, step = lib.setup(Path(sys.argv[1]).read_bytes())
for n, ids in enumerate(([0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 0, 1, 2, 3])):
    e.load_state(state)
    chaz = [e.peek(0xFFF500 + i) for i in range(0x80)]
    for cid in ids[1:]:
        if cid:
            for i, b in enumerate(chaz):
                e.poke(0xFFF500 + cid * 0x80 + i, b)
    for i in range(6):
        e.poke(0xFFF40A + i, ids[i] if i < len(ids) else 0xFF)
    lib.do_step(e, step)
    e.run(150)
    e.screenshot(out / f"battle_grupo{n}.png")
    W, H, img, cells = lib.plane_a(e, lambda t, cy: 15 <= cy <= 20 and 0 < t < 1664)
    # As 5 posições são vizinhas, de 6 células (48 px) cada, a partir da primeira coluna ocupada.
    c0 = min(cx for cx, cy in cells)
    for pos in range(5):
        cid = ids[SCREEN_ORDER[pos]]
        if n == 2 and cid != 10:
            continue  # o grupo 3 só serve para o Seth
        part = [c for c in cells if (c[0] - c0) // 6 == pos]
        if not part:
            continue
        w, h, data = lib.crop(W, img, part)
        png(out / f"battle_{cid:02d}_{NAMES[cid]}.png", w, h, data)
        print(NAMES[cid], w, h)
