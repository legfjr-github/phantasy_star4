"""Combos: técnicas/skills de vários personagens que, usadas em sequência no mesmo turno, viram um
ataque combinado.

Como o jogo detecta (rotina 0x27DE7C, em cada ação da fase de execução):
- monta os códigos das próximas ações do turno, na ordem em que vão acontecer (FFEFAC): para cada uma,
  o comando em FF4106 + membro*4 (byte alto 2 = técnica, 3 = skill; byte baixo = ID). Código =
  ID da técnica, ou 0x80 + ID da skill. A técnica precisa de TP suficiente (custo em 0x2A9BE1 + id*8);
  a skill precisa ter usos no slot (+0x6A) e o bit 7 em 0x2A9D21 + id*8. Personagem com status em
  +0x16 & 0xCE interrompe a sequência.
- compara com as 14 entradas de 0x28549C: 1º byte = quantidade de ações (2, 3 ou 4; o bit 0x80
  marca as entradas cuja lista traz as ordens alternativas), depois as combinações aceitas, até FF.
- achando, grava 0x800 + número do combo em FF4146 e pula as ações consumidas (0x27DFA8).
Nomes dos combos na lista 0x28554C.

Captura: o grupo tem um membro por ação (Chaz, Alys, Hahn, Rune, com a ficha do Chaz copiada), cada
um com a técnica ou skill no 1º slot, TP 999 e usos 9; a agilidade (+0x1E..+0x20) cai do 1º ao último
para a ordem do turno ser a do grupo. Cada um escolhe a ação no menu de ícones (direita 1x técnica,
2x skill; C abre a lista; C escolhe; C no alvo, se o jogo pedir). Grava 400 quadros depois do último
comando e confirma que FF4146 = 0x800 + número do combo.
Saída: assets/combos/combo_<n>_<nome>.gif, _folha.png e combos.csv.
Uso: combo_gifs.py <preload.state> [primeiro último]
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import battlelib as lib  # noqa: E402
from ps4emu import C, RIGHT  # noqa: E402
from PIL import Image  # noqa: E402

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "combos"
out.mkdir(parents=True, exist_ok=True)
first, last = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1, 14)

src = (root / "tools" / "export_game_data.py").read_text(encoding="utf-8")
env = {"rom": rom, "re": re}
for fn in ("upper_name", "name_list"):
    exec(re.search(r"def %s\(.*?\n(?=\S)" % fn, src, re.S).group(0), env)
NAMES = env["name_list"](0x2AAFB4, 0x2ABC00)
COMBO_NAMES = env["name_list"](0x28554C, 0x285630)[:14]


def act_name(c):
    return (NAMES[199 + (c & 0x7F)] + " (skill)") if c & 0x80 else NAMES[159 + c]


def combo_table():
    p, table = 0x28549C, []
    for _ in range(14):
        kind = rom[p]
        n = kind & 0x7F
        p += 1
        seqs = []
        while rom[p] != 0xFF:
            seqs.append(tuple(rom[p:p + n]))
            p += n
        p += 1
        table.append((kind, seqs))
    return table


TABLE = combo_table()
e, state, step = lib.setup(Path(sys.argv[1]).read_bytes())


def poke16(a, v):
    e.poke(a, v >> 8)
    e.poke(a + 1, v & 0xFF)


def frame_image(snap):
    w, h = snap["size"]
    raw = snap["frame"]
    img = Image.new("RGB", (w, h))
    px = img.load()
    for i in range(w * h):
        v = raw[i * 2] | raw[i * 2 + 1] << 8
        px[i % w, i // w] = (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31)
    return img


def run_combo(seq):
    e.load_state(state)
    members = list(range(len(seq)))  # Chaz, Alys, Hahn, Rune
    chaz = [e.peek(0xFFF500 + i) for i in range(0x80)]
    for k, cid in enumerate(members):
        base = 0xFFF500 + cid * 0x80
        if cid:
            for i, b in enumerate(chaz):
                e.poke(base + i, b)
        for off in (0x0E, 0x10, 0x12, 0x14):
            poke16(base + off, 999)
        for off in (0x1E, 0x1F, 0x20):
            e.poke(base + off, 250 - k * 40)
        code = seq[k]
        if code & 0x80:
            e.poke(base + 0x62, code & 0x7F)
            e.poke(base + 0x6A, 9)
            e.poke(base + 0x6B, 9)
        else:
            e.poke(base + 0x52, code)
    for i in range(6):
        e.poke(0xFFF40A + i, members[i] if i < len(members) else 0xFF)
    lib.do_step(e, step)
    # Estado do menu de batalha em FF4108: 2 = janela COMD/MACR/RUN, 5 = barra de ícones,
    # 8 = lista de técnicas, 0x11 = lista de skills, 0xC = escolha do alvo. O inimigo às vezes age primeiro, então
    # cada passo espera o estado certo em vez de contar quadros.
    def wait(state, limit=900):
        for _ in range(limit):
            if e.peek(0xFF4108, 2) == state:
                return True
            e.run(1)
        return False

    if not wait(2):
        return [], False, 0
    e.press(C, 3, 10)  # COMD
    for k, code in enumerate(seq):
        if not wait(5):
            return [], False, 0
        for _ in range(2 if code & 0x80 else 1):
            e.press(RIGHT, 3, 10)
        e.press(C, 3, 10)  # abre a lista
        if not wait(0x11 if code & 0x80 else 8, 120):  # lista de skills = 0x11
            return [], False, 0
        e.press(C, 3, 10)  # escolhe o 1º
        e.run(10)
        if e.peek(0xFF4108, 2) == 0xC:
            e.press(C, 3, 10)  # alvo
    e.trace(True)
    frames, flags = [], set()
    for _ in range(100):
        flags.add(e.peek(0xFF4146, 2))  # o valor é sobrescrito no turno seguinte
        e.run(4)
        frames.append(frame_image(lib.snapshot(e)))
    combo = next((f for f in flags if f & 0xFF00 == 0x800), 0)
    return frames, bool(combo), combo


rows = []
for n in range(first, last + 1):
    kind, seqs = TABLE[n - 1]
    name = COMBO_NAMES[n - 1]
    frames, ok, flag = run_combo(seqs[0])
    safe = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    if not frames:
        print(n, name, "menu não respondeu")
        continue
    frames[0].save(out / f"combo_{n:02d}_{safe}.gif", save_all=True, append_images=frames[1:], duration=60, loop=0)
    sheet = Image.new("RGB", (5 * 160, 5 * 112))
    for k, fr in enumerate(frames[::4][:25]):
        sheet.paste(fr.resize((160, 112)), ((k % 5) * 160, (k // 5) * 112))
    sheet.save(out / f"combo_{n:02d}_{safe}_folha.png")
    alts = sorted({" + ".join(act_name(c) for c in s) for s in seqs})
    rows.append({"combo": n, "nome": name, "acoes": len(seqs[0]),
                 "ordem_livre": "sim" if kind & 0x80 else "não",
                 "combinacoes_aceitas": " | ".join(alts), "capturado": "sim" if flag == 0x800 + n else "não",
                 "ff4146": f"{flag:04X}"})
    print(rows[-1]["combo"], name, "capturado" if flag == 0x800 + n else "NÃO disparou", f"{flag:04X}")
if first == 1 and last == 14:
    with open(out / "combos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
