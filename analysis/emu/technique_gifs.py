"""Animações das técnicas e skills, gravadas em batalha.

Os gráficos dos efeitos são listas de tiles Nemesis (tabelas 0x27E88A e 0x27EA66, carregadas por
0x41880) montadas quadro a quadro em sprites, com paleta própria; soltos não formam imagem. Então o
script faz o personagem usar cada uma e grava a tela:
- parte do encontro de battlelib (masmorra, estado e passo reproduzíveis);
- antes do passo, põe a técnica t no 1º slot do Chaz (FFF552) ou a skill no 1º slot de skill
  (FFF562, com usos 9/9 em FFF56A) e TP/HP 999;
- no menu: C (COMD), direita 1x (técnica) ou 2x (skill), C (lista), C (1º item), C (alvo);
- grava 240 quadros (um a cada 3) e salva GIF e uma folha com 1 quadro a cada 12.
Nomes: lista 0x2AAFB4, técnica t = índice 159+t (o Chaz começa com a 24, RES), skills a partir do 200.
Saída: assets/techniques/<tipo>_<id>_<nome>.gif e _folha.png.
Uso: technique_gifs.py <preload.state> [tecnicas|skills] [primeiro último [testar]]
("testar" tenta os 11 personagens até a animação aparecer; RYUKA e HINAS são só de campo.)
"""
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
out = root / "assets" / "techniques"
out.mkdir(parents=True, exist_ok=True)
kind = sys.argv[2] if len(sys.argv) > 2 else "tecnicas"
first, last = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else ((1, 40) if kind == "tecnicas" else (1, 54))


def names():
    """Lista de nomes 0x2AAFB4 (mesmo formato de export_game_data.name_list)."""
    src = (root / "tools" / "export_game_data.py").read_text(encoding="utf-8")
    env = {"rom": rom, "re": re}
    for fn in ("upper_name", "name_list"):
        exec(re.search(r"def %s\(.*?\n(?=\S)" % fn, src, re.S).group(0), env)
    return env["name_list"](0x2AAFB4, 0x2ABC00)


NAMES = names()
e, state, step = lib.setup(Path(sys.argv[1]).read_bytes())


def frame_image(snap):
    w, h = snap["size"]
    raw = snap["frame"]
    img = Image.new("RGB", (w, h))
    px = img.load()
    for i in range(w * h):
        v = raw[i * 2] | raw[i * 2 + 1] << 8
        px[i % w, i // w] = (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31)
    return img


def poke16(a, v):
    e.poke(a, v >> 8)
    e.poke(a + 1, v & 0xFF)


def record(n, caster):
    """Usa a técnica/skill n e devolve os quadros gravados. caster 0: o Chaz sozinho. Outro número:
    grupo Chaz + caster (com a ficha do Chaz copiada); o Chaz defende e o caster usa a técnica.
    (Com o caster sozinho no grupo o menu não sai do COMD.)"""
    e.load_state(state)
    base = 0xFFF500 + caster * 0x80
    if caster:
        chaz = [e.peek(0xFFF500 + i) for i in range(0x80)]
        for i, b in enumerate(chaz):
            e.poke(base + i, b)
        for i in range(6):
            e.poke(0xFFF40A + i, (0, caster)[i] if i < 2 else 0xFF)
    for b in {0xFFF500, base}:
        for off in (0x0E, 0x10, 0x12, 0x14):  # HP e TP máximos e atuais
            poke16(b + off, 999)
    if kind == "tecnicas":
        e.poke(base + 0x52, n)
        rights = 1
    else:
        e.poke(base + 0x62, n)
        e.poke(base + 0x6A, 9)
        e.poke(base + 0x6B, 9)
        rights = 2
    lib.do_step(e, step)
    e.run(150)
    e.press(C, 3, 20)
    if caster:
        for btn in [RIGHT] * 4 + [C]:  # Chaz: defender (5º ícone)
            e.press(btn, 3, 15)
    for _ in range(rights):
        e.press(RIGHT, 3, 12)
    e.press(C, 3, 20)
    e.press(C, 3, 20)
    e.press(C, 3, 10)
    frames = []
    for f in range(80):
        e.run(3)
        frames.append(frame_image(lib.snapshot(e)))
    return frames


def motion(frames):
    """Maior fração de pixels que mudou em relação ao primeiro quadro, acima da barra de status
    (as janelas de menu e o cursor piscando ficam fora da conta)."""
    w = frames[0].width
    first = frames[0].crop((96, 0, w, 160)).tobytes()
    best = 0
    for fr in frames[1::4]:
        b = fr.crop((96, 0, w, 160)).tobytes()
        best = max(best, sum(1 for i in range(0, len(b), 12) if abs(b[i] - first[i]) > 30) / (len(b) // 12))
    return best


# 15 skills não têm animação quando o Chaz as usa sozinho; com o argumento "testar", usa o grupo
# Chaz + outro personagem (Rune primeiro) até aparecer movimento (mais de 3% da área).
casters = [3, 1, 2, 4, 5, 6, 7, 8, 9, 10] if len(sys.argv) > 5 and sys.argv[5] == "testar" else [0]
for n in range(first, last + 1):
    if kind == "tecnicas":
        name, tag = NAMES[159 + n], f"tecnica_{n:02d}"
    else:
        name, tag = NAMES[199 + n], f"skill_{n:02d}"
    for caster in casters:
        frames = record(n, caster)
        if motion(frames) > 0.03:
            break
    safe = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    frames[0].save(out / f"{tag}_{safe}.gif", save_all=True, append_images=frames[1:], duration=50, loop=0)
    sheet_frames = frames[::4]
    sheet = Image.new("RGB", (5 * 160, ((len(sheet_frames) + 4) // 5) * 112))
    for k, fr in enumerate(sheet_frames):
        sheet.paste(fr.resize((160, 112)), ((k % 5) * 160, (k // 5) * 112))
    sheet.save(out / f"{tag}_{safe}_folha.png")
    print(tag, name, "personagem", caster, "movimento", round(motion(frames) * 100, 1))
