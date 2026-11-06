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
Os tiles do inimigo vêm depois dos do grupo (no estado usado, só o Chaz, tiles 390-406) até o fim
da área reservada pelo carregador (FFEE54/32). O recorte usa o quadro em que o inimigo tem mais
células no plano A (ver battle_with) e a paleta do quadro 150.
Só os IDs 0-152 são inimigos (a tabela de gráficos 0x27F3B8 tem 153 entradas); depois deles a lista
de nomes segue com nomes de ataques.

Saída: assets/enemies/enemy_<id>.png (tela), enemy_<id>_spr.png (só o inimigo, recortado),
fixed_<n>.png e enemies_gallery.csv. Uso: enemy_gallery.py <preload.state> [primeiro último [formações fixas, ex. 9,26]]
"""
import csv
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import battlelib as lib  # noqa: E402
from ps4emu import C  # noqa: E402
from pngutil import png  # noqa: E402
from sega_codecs import kosinski  # noqa: E402

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "enemies"
out.mkdir(parents=True, exist_ok=True)
first, last = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 152)
only_fixed = {int(x) for x in sys.argv[4].split(",")} if len(sys.argv) > 4 else None
FREE = 0x2F5000

names = [r["nome"] for r in csv.DictReader(open(root / "assets" / "data" / "enemies.csv", encoding="utf-8"))]
e, state, step = lib.setup(Path(sys.argv[1]).read_bytes())


def battle_with(record, tag):
    e.patch_rom(FREE, record + b"\xff" * (32 - len(record)))
    e.load_state(state)
    for a in (0xFFF50E, 0xFFF510):  # HP máximo e atual do Chaz = 999, para a batalha não acabar em derrota
        e.poke(a, 0x03)
        e.poke(a + 1, 0xE7)
    e.trace(True)
    lib.do_step(e, step)
    if not e.executed(0x7F5E):
        return "sem batalha"
    # Muitos inimigos começam inteiros no plano A e, quando a animação de espera começa, o jogo apaga
    # parte das células e passa a desenhar esse pedaço como sprite; outros (Zio) só aparecem depois.
    # Então acompanha 200 quadros e fica com a VRAM do quadro em que o inimigo tem mais células no
    # plano A. Os tiles do inimigo vão de 407 (depois dos do grupo) até FFEE54/32, o fim da área
    # que o carregador reservou; isso deixa de fora os números de dano e as janelas.
    # Fantasmas e vermes são desenhados como sprites, e chefes enormes no plano B, então a contagem
    # e o desenho somam os três (battlelib.enemy_tiles / enemy_image).
    # Fantasmas, Dimensworm e as formas do Dark Force só aparecem quando o turno anda, então a partir
    # do quadro 200 aperta C a cada 40 (o Chaz ataca). Fica com o primeiro quadro em que o inimigo
    # tem pelo menos 90% dos tiles do máximo (evita escolher um quadro de ataque, com efeitos), e
    # com a paleta e a tela desse quadro, nunca antes do 100 (fim do esmaecimento de entrada).
    # Fase 1: 300 quadros sem apertar nada; o quadro é escolhido só pelos planos (os sprites desse
    # começo costumam ser efeitos do próprio inimigo), mas o desenho inclui os sprites.
    snaps = []
    for frame in range(5, 305, 5):
        e.run(5)
        hi = e.peek(0xFFEE54, 2) // 32
        snap = lib.snapshot(e)
        snaps.append((frame, hi, lib.enemy_tiles(snap, 407, hi, sprites=False), snap))
    top = max(n for _, _, n, _ in snaps)
    frame, hi, _, snap = next(s for s in snaps if s[2] >= 0.9 * top and s[2] > 0) if top else snaps[-1]
    # Paleta: a mais clara entre os quadros a partir do escolhido (e do 100). Os chefes finais entram
    # no escuro e a paleta sobe aos poucos; sem apertar nada, nenhum ataque pisca a tela nessa fase.
    pal_snap = max((s[3] for s in snaps if s[0] >= max(frame, 100)),
                   key=lambda sn: sum(struct.unpack_from("<64H", sn["cram"])))
    spr = lib.enemy_image(snap, pal_snap["cram"], 407, hi)
    # Silhuetas de entrada (sombra preta ou nuvem branca dos chefes finais) têm pouquíssimas cores.
    colors = len({spr[2][k:k + 4] for k in range(0, len(spr[2]), 4)}) if spr else 0
    if not spr or spr[0] * spr[1] < 256 or colors <= 5:
        # Fase 2: o inimigo ainda não apareceu (fantasmas, Dimensworm, formas do Dark Force). Aperta C
        # a cada 40 quadros para o turno andar e escolhe o quadro com mais pixels do inimigo. O início
        # da faixa passa a ser o menor tile que o inimigo usa nos planos, para deixar de fora os efeitos
        # do ataque do Chaz (sprites logo depois dos tiles do grupo).
        lo = lib.min_plane_tile(snap, 407, hi) or 407
        best = None
        for frame in range(305, 705, 5):
            e.run(5)
            if frame % 40 == 0:
                e.press(C, 3, 5)
            if frame % 10:
                continue
            hi = e.peek(0xFFEE54, 2) // 32
            s = lib.snapshot(e)
            img = lib.enemy_image(s, s["cram"], lib.min_plane_tile(s, 407, hi) or lo, hi)
            if not img:
                continue
            px = sum(1 for k in range(3, len(img[2]), 4) if img[2][k])
            ncol = len({img[2][k:k + 4] for k in range(0, len(img[2]), 4)})
            score = px * min(ncol, 16)  # silhueta de uma cor perde para a forma colorida
            if best is None or score > best[0]:
                best = (score, frame, s, img)
        if best and best[0]:
            _, frame, pal_snap, spr = best
    ok = not e.executed(0x200)
    lib.save_frame(pal_snap, out / f"{tag}.png")
    (out / f"{tag}_cram.bin").write_bytes(pal_snap["cram"])
    if spr:
        png(out / f"{tag}_spr.png", *spr)
    return ("ok" if ok else "travou") + f" (recorte do quadro {frame})"


e.patch_rom(0x7F00, bytes.fromhex("41F9") + FREE.to_bytes(4, "big"))
e.patch_rom(0x7F06, bytes.fromhex("600C"))
rows = []
for i in range(first, last + 1):
    st = battle_with(bytes.fromhex("1000088001 0100") + bytes((i, 0x14, 0xFF)), f"enemy_{i:03d}")
    rows.append({"tipo": "inimigo", "id": i, "nome": names[i] if i < len(names) else "", "resultado": st})
    print(rows[-1])
fixed, _ = kosinski(rom, 0x284F7C)
for n, rec in enumerate(fixed.split(b"\xff")):
    if len(rec) < 7 or (only_fixed is not None and n not in only_fixed):
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
