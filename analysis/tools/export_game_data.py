"""Exporta as tabelas de dados do jogo em CSV (assets/data/) e o mapa de zonas de encontro em PNG.

Fontes, todas confirmadas pelo código que as lê:
- Inimigos: 0x2816BC, 48 bytes por ID, copiados pelo carregador 0x7F5E para o objeto de batalha
  (mesma estrutura de 0x80 bytes dos personagens: HP em +0x0E, atributos em +0x18.., XP +0x60,
  meseta +0x62). Nome = lista de nomes 0x280D07, índice ID+8 (os 8 primeiros são as classes).
- Formações: 4 listas Kosinski de 128 (0x283E6C, 0x2842BC, 0x28471C, 0x284B8C), lidas em 0x7EBA.
  Formato: 4 bytes de cabeçalho, N inimigos, 2 máscaras, N pares (ID, posição X).
- Zonas: Kosinski 0x2836EC, 64 bytes por zona = 32 IDs de formação sorteados por (rand & 0x1F).
- Mapa de zonas: Kosinski 0x28501C (Motavia, 64x64) e 0x2853CC (64x32), célula = 64 px.
- Formações fixas (chefes e eventos): Kosinski 0x284F7C, quando FFECFC >= 0.
- Itens: registros de 22 bytes em 0x2A8E3A (leitor 0x27DE38), nomes em 0x2AAFB4.
- Lojas: listas de até 6 IDs terminadas em FF em 0x681A6-0x6829D (código de loja em 0x658F6).
"""
import csv
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pngutil import png  # noqa: E402
from sega_codecs import kosinski  # noqa: E402

here = Path(__file__).resolve().parent.parent
rom = (here / "ps4.bin").read_bytes()
out = here / "assets" / "data"
out.mkdir(parents=True, exist_ok=True)


def upper_name(b):
    """Nomes das tabelas: 01-1A = A-Z, 39-52 = a-z, 31/00 = espaço, 53 = '-'."""
    s = ""
    for x in b:
        if 1 <= x <= 26:
            s += chr(64 + x)
        elif 0x39 <= x <= 0x52:
            s += chr(97 + x - 0x39)
        elif x in (0x00, 0x31):
            s += " "
        elif x == 0x53:
            s += "-"
        else:
            s += "?"
    return s.strip()


def name_list(start, end):
    return [upper_name(p) for p in re.split(rb"[\xfe\xff]", rom[start:end])]


def write_csv(name, rows):
    with open(out / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} linhas")


# ---- Inimigos
names = name_list(0x280D07, 0x2816BC)
ENEMY_BASE, ENEMY_SIZE = 0x2816BC, 48
n_enemies = len(names) - 8
enemies = []
for i in range(n_enemies):
    e = rom[ENEMY_BASE + i * ENEMY_SIZE:ENEMY_BASE + (i + 1) * ENEMY_SIZE]
    enemies.append({
        "id": i, "nome": names[i + 8],
        "hp": struct.unpack_from(">H", e, 0)[0],
        "campo_12": e[2], "campo_14": e[3],          # bytes copiados para +0x12/+0x14 (TP nos personagens)
        "forca": e[4], "mental": e[5], "agilidade": e[6], "destreza": e[7],
        "ataque": struct.unpack_from(">H", e, 8)[0],
        "defesa": e[10], "defesa_2": e[11],          # +0x28 e +0x2C do objeto de batalha
        "resistencias": e[0x0C:0x1A].hex(" "),       # 14 bytes -> +0x30..+0x4B
        "acoes": e[0x1C:0x2C].hex(" "),              # 16 bytes -> +0x50..+0x5F
        "xp": struct.unpack_from(">H", e, 0x2C)[0],
        "meseta": struct.unpack_from(">H", e, 0x2E)[0],
    })
write_csv("enemies.csv", enemies)


def enemy_name(i):
    return enemies[i]["nome"] if 0 <= i < len(enemies) else f"#{i}"


# ---- Formações
formations = []
for lst, base in enumerate((0x283E6C, 0x2842BC, 0x28471C, 0x284B8C)):
    data, _ = kosinski(rom, base)
    for k, f in enumerate(data.split(b"\xff")[:128]):
        if len(f) < 7:
            continue
        n = f[4]
        pairs = [(f[7 + j * 2], f[8 + j * 2]) for j in range(n) if 8 + j * 2 < len(f)]
        formations.append({
            "id": lst * 128 + k, "cabecalho": f[:4].hex(" "), "qtd": n, "mascaras": f[5:7].hex(" "),
            "inimigos": " | ".join(f"{enemy_name(e)} (x={x})" for e, x in pairs),
        })
write_csv("formations.csv", formations)

fixed, _ = kosinski(rom, 0x284F7C)
write_csv("formations_fixed.csv", [
    {"id": k, "bytes": f.hex(" ")} for k, f in enumerate(fixed.split(b"\xff")) if f])

# ---- Zonas
zones_raw, _ = kosinski(rom, 0x2836EC)
form_by_id = {f["id"]: f["inimigos"] for f in formations}
zones = []
for z in range(len(zones_raw) // 64):
    ids = struct.unpack_from(">32H", zones_raw, z * 64)
    counts = {}
    for x in ids:
        counts[x] = counts.get(x, 0) + 1
    zones.append({
        "zona": z,
        "formacoes": " ; ".join(f"{fid}[{c}/32]: {form_by_id.get(fid, '?')}" for fid, c in sorted(counts.items())),
    })
write_csv("zones.csv", zones)

# ---- Mapa de zonas em PNG (cor por zona)
for label, base, rows in (("motavia", 0x28501C, 64), ("mapa2", 0x2853CC, 32)):
    grid, _ = kosinski(rom, base)
    img = bytearray(64 * rows * 4)
    for i, z in enumerate(grid[:64 * rows]):
        if z >= 0x80:
            c = (20, 20, 20)
        else:
            c = ((z * 97) % 200 + 55, (z * 57) % 200 + 55, (z * 31) % 200 + 55)
        img[i * 4:i * 4 + 4] = bytes((*c, 255))
    scale = 4
    big = bytearray()
    for y in range(rows):
        line = b"".join(img[(y * 64 + x) * 4:(y * 64 + x) * 4 + 4] * scale for x in range(64))
        big += line * scale
    png(out / f"zones_{label}.png", 64 * scale, rows * scale, bytes(big))
    write_csv(f"zones_{label}_grid.csv", [{"linha": y, "zonas": " ".join(
        "--" if b >= 0x80 else f"{b:02X}" for b in grid[y * 64:(y + 1) * 64])} for y in range(rows)])

# ---- Níveis: ponteiros em 0x5D73A (um por personagem, na ordem da lista 0x280CD0), 98 registros
# de 22 bytes (níveis 2-99): XP necessário (32 bits), HP máx, TP máx, Força, Mental, Agilidade,
# Destreza e 10 bytes ainda sem nome. Achado lendo o que a tela de status consulta para "NX".
char_names = [upper_name(rom[0x280CD0 + i * 5:0x280CD0 + i * 5 + 4]) for i in range(11)]
levels = []
for c in range(11):
    ptr = struct.unpack_from(">I", rom, 0x5D73A + c * 4)[0]
    prev_xp = -1
    for lv in range(2, 100):
        r = rom[ptr + (lv - 2) * 22:ptr + (lv - 1) * 22]
        xp, hp, tp = struct.unpack_from(">IHH", r, 0)
        if xp <= prev_xp:  # a tabela do último personagem (convidado) é mais curta
            break
        prev_xp = xp
        # Bytes 12-13: técnica/skill aprendida no nível (IDs; 0 = nada). Bytes 14-21: máximo de usos
        # de cada um dos 8 slots de skill, que vão para os pares atual/máx em +0x6A da estrutura
        # (Chaz LV1 tem 3/3 usos de Crosscut; o registro do LV2 traz 4).
        levels.append({"personagem": char_names[c], "nivel": lv, "xp": xp, "hp_max": hp, "tp_max": tp,
                       "forca": r[8], "mental": r[9], "agilidade": r[10], "destreza": r[11],
                       "aprende_1": r[12], "aprende_2": r[13],
                       "usos_skill": " ".join(str(x) for x in r[14:22])})
write_csv("levels.csv", levels)

# ---- Itens
item_names = name_list(0x2AAFB4, 0x2AB702)
items = []
for i, nm in enumerate(item_names[:200], start=1):
    r = rom[0x2A8E3A + (i - 1) * 22:0x2A8E3A + i * 22]
    items.append({
        "id": i, "nome": nm, "tipo": "arma" if r[0] & 1 else "outro",
        "preco": struct.unpack_from(">H", r, 2)[0],
        "equipa_mascaras": r[12:15].hex(" "), "bonus_13": r[19], "bonus_14": r[20],
        "bytes": r.hex(" "),
    })
write_csv("items.csv", items)

# ---- Lojas
shops = []
start = a = 0x681A6
while a <= 0x6829D + 8:
    if rom[a] == 0xFF:
        seg = rom[start:a]
        if seg and all(1 <= x <= 200 for x in seg):
            shops.append({"rom": f"{start:06X}", "itens": " | ".join(
                f"{item_names[x - 1]} ({items[x - 1]['preco']})" for x in seg)})
        start = a + 1
    a += 1
write_csv("shops.csv", shops)
