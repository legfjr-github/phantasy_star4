"""Quadros ilustrados das cenas (o comando de texto F2 00 hhll, rotina 0x6AF9C).

0x6B290 acha o registro: a tabela 0x6B2B6 tem 7 ponteiros, um para cada grupo de 64 IDs (id >> 6), e
cada registro tem 30 bytes (id & 0x3F). O registro é copiado para FFED10:
  +00 tile de destino na VRAM (FFFF = sem gráfico novo)   +02 ponteiro Nemesis dos tiles
  +06 largura e altura em células                           +08 coluna e linha na tela
  +0A atributo base do mapa (bits 13-14 = linha de paleta)  +0C ponteiro da paleta (16 cores)
  +10 ponteiro Enigma do mapa de tiles
  +14/+16/+1A segunda camada com o mesmo formato (atributo, paleta, Enigma; FFFF = não tem)
A primeira camada vai para um plano e a segunda para o outro, na mesma posição; aqui a segunda é
desenhada por baixo e a primeira por cima, com a cor 0 transparente.
Os tiles podem vir de um quadro anterior (destino FFFF ou tiles já carregados): o script carrega os
gráficos de todos os registros do mesmo grupo em ordem, como acontece numa cena.
Saída: assets/panels/panel_<id>.png e panels.csv (IDs usados no diálogo e campos de cada registro).
"""
import csv
import re
import struct
from pathlib import Path

from pngutil import png
from sega_codecs import enigma, nemesis

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "panels"
out.mkdir(parents=True, exist_ok=True)
FMT = ">HIBBBBHIIHII"

used = {}
dialogue = (root / "assets" / "text" / "dialogue.txt").read_text(encoding="utf-8")
for m in re.finditer(r"\{panel:([0-9A-F]{4})\}", dialogue):
    used[int(m.group(1), 16)] = used.get(int(m.group(1), 16), 0) + 1


def valid_ptr(p):
    return 0x70000 <= p < 0x300000  # os gráficos do grupo 0 começam em 0x7B780


def colors(p):
    pal = []
    for c in struct.unpack_from(">16H", rom, p):
        r, g, b = (c >> 1) & 7, (c >> 5) & 7, (c >> 9) & 7
        pal.append(bytes((r * 255 // 7, g * 255 // 7, b * 255 // 7, 255)))
    return pal


def draw(img, W, vram, data, w, h, pal, transparent):
    words = struct.unpack_from(f">{min(len(data) // 2, w * h)}H", data)  # Enigma devolve palavras big-endian
    for i, ent in enumerate(words):
        cx, cy = i % w, i // w
        t, hf, vf = ent & 0x7FF, ent & 0x800, ent & 0x1000
        for y in range(8):
            row = vram[t * 32 + (7 - y if vf else y) * 4:][:4]
            for x in range(8):
                sx = 7 - x if hf else x
                c = (row[sx >> 1] >> (0 if sx & 1 else 4)) & 15
                if c or not transparent:
                    o = ((cy * 8 + y) * W + cx * 8 + x) * 4
                    img[o:o + 4] = pal[c]


rows = []
for g in range(7):
    base = struct.unpack_from(">I", rom, 0x6B2B6 + g * 4)[0]
    vram = bytearray(0x10000)
    for k in range(64):
        pid = g * 64 + k
        t, nem, w, h, x, y, attr, pal, eni, attr2, pal2, eni2 = struct.unpack_from(FMT, rom, base + k * 30)
        if not (0 < w <= 40 and 0 < h <= 28 and valid_ptr(eni) and valid_ptr(pal)
                and (t == 0xFFFF or valid_ptr(nem))):
            continue
        if t != 0xFFFF:
            tiles, _ = nemesis(rom, nem)
            vram[t * 32:t * 32 + len(tiles)] = tiles[:0x10000 - t * 32]
        W, H = w * 8, h * 8
        img = bytearray(W * H * 4)
        if attr2 != 0xFFFF and valid_ptr(eni2) and valid_ptr(pal2):
            words, _ = enigma(rom, eni2, attr2)
            draw(img, W, vram, words, w, h, colors(pal2), False)
            words, _ = enigma(rom, eni, attr)
            draw(img, W, vram, words, w, h, colors(pal), True)
        else:
            words, _ = enigma(rom, eni, attr)
            draw(img, W, vram, words, w, h, colors(pal), False)
        png(out / f"panel_{pid:04X}.png", W, H, bytes(img))
        rows.append({"id": f"{pid:04X}", "usos_no_dialogo": used.get(pid, 0), "tiles_vram": f"{t:04X}",
                     "nemesis": f"{nem:06X}", "largura": w, "altura": h, "coluna": x, "linha": y,
                     "atributo": f"{attr:04X}", "paleta": f"{pal:06X}", "enigma": f"{eni:06X}",
                     "camada2": "" if attr2 == 0xFFFF else f"{attr2:04X} {pal2:06X} {eni2:06X}"})
with open(out / "panels.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=rows[0].keys())
    wr.writeheader()
    wr.writerows(rows)
print(len(rows), "quadros;", sum(1 for r in rows if r["usos_no_dialogo"]), "usados no diálogo;",
      len(used), "IDs citados no diálogo;", sorted(f"{i:04X}" for i in used if f"{i:04X}" not in {r['id'] for r in rows}))
