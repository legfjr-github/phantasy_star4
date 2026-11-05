"""Formato das músicas (driver SMPS do 68000 em 0xD0008): cabeçalhos, trilhas e instrumentos FM.

Confirmado pelo rastreio do emulador (o que o driver lê ao receber o comando em FF500A):
- Tabela de músicas em 0xD1C40: ponteiro de 32 bits por ID, a partir de 0x81.
- Cabeçalho: +0 deslocamento da tabela de instrumentos (relativo ao cabeçalho), +2 nº de trilhas FM
  (a primeira é o DAC), +3 nº de trilhas PSG, +4 divisor de andamento, +5 andamento; depois cada trilha
  FM/DAC = (deslocamento 16 bits, transposição, volume) e cada PSG = (deslocamento, transposição,
  volume, modulação, instrumento PSG).
- Instrumento FM: 25 bytes no formato SMPS (algoritmo/feedback e os registradores dos 4 operadores).
- Comandos de trilha: 00-7F duração, 80 pausa, 81-DF nota, E0-FF controle (tabela de saltos 0xD1038;
  FF lê um subcódigo). Bytes de argumento por comando em ARGS (lidos nos tratadores; os marcados
  com ? desviam para código compartilhado e foram conferidos só pela contagem de leituras).
Saída: assets/sound/smps_songs.csv e smps_voices.csv.
"""
import csv
import struct
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "sound"
out.mkdir(parents=True, exist_ok=True)

ARGS = {0xE0: 1, 0xE1: 1, 0xE2: 1, 0xE3: 1, 0xE4: 1, 0xE5: 2, 0xE6: 1, 0xE7: 0, 0xE8: 1, 0xE9: 2,
        0xEA: 1, 0xEB: 1, 0xEC: 1, 0xED: 1, 0xEE: 1, 0xEF: 1, 0xF0: 4, 0xF1: 2, 0xF2: 0, 0xF3: 1,
        0xF4: 1, 0xF5: 1, 0xF6: 2, 0xF7: 4, 0xF8: 2, 0xF9: 0, 0xFA: 1, 0xFB: 1, 0xFC: 1, 0xFD: 1,
        0xFE: 1, 0xFF: 1}
NAMES = {0xE0: "pan", 0xE1: "detune", 0xE6: "volume", 0xE7: "liga", 0xE8: "duração_nota", 0xEA: "andamento",
         0xEE: "sample_DAC", 0xEF: "instrumento", 0xF0: "modulação", 0xF2: "fim", 0xF3: "ruído_PSG",
         0xF5: "instrumento_PSG", 0xF6: "salto", 0xF7: "repetição", 0xF8: "chamada", 0xF9: "retorno",
         0xFB: "transposição"}

ids = [s for s in range(0x81, 0xB5)]
songs, voices = [], []
for sid in ids:
    h = struct.unpack_from(">I", rom, 0xD1C40 + (sid - 0x81) * 4)[0]
    if not 0xD0000 <= h < 0x100000:
        continue
    voice_off, n_fm, n_psg, div, tempo = struct.unpack_from(">HBBBB", rom, h)
    p = h + 6
    tracks = []
    for k in range(n_fm):
        off, tr, vol = struct.unpack_from(">HbB", rom, p)
        tracks.append(("DAC" if k == 0 else f"FM{k}", h + off, tr, vol))
        p += 4
    for k in range(n_psg):
        off, tr, vol, mod, inst = struct.unpack_from(">HbBBB", rom, p)
        tracks.append((f"PSG{k + 1}", h + off, tr, vol))
        p += 6
    # comandos usados em cada trilha (até o primeiro fim/salto de volta), só para contagem
    used = {}
    for name, start, _, _ in tracks:
        q, steps = start, 0
        while steps < 4000 and q < len(rom):
            b = rom[q]
            q += 1
            steps += 1
            if b >= 0xE0:
                used[b] = used.get(b, 0) + 1
                if b in (0xF2, 0xF6):
                    break
                q += ARGS[b]
    songs.append({"id": f"{sid:02X}", "cabecalho": f"{h:06X}", "trilhas_fm": n_fm, "trilhas_psg": n_psg,
                  "divisor": div, "andamento": tempo, "instrumentos": f"{h + voice_off:06X}",
                  "trilhas": " ".join(f"{n}@{a:06X}(tr{t:+d},v{v:02X})" for n, a, t, v in tracks),
                  "comandos": " ".join(f"{NAMES.get(c, f'{c:02X}')}x{n}" for c, n in sorted(used.items()))})
    first_track = min(a for _, a, _, _ in tracks)
    vt = h + voice_off
    n_voices = max(0, min(40, (first_track - vt) // 25)) if first_track > vt else 16
    for v in range(n_voices):
        data = rom[vt + v * 25:vt + v * 25 + 25]
        voices.append({"musica": f"{sid:02X}", "instrumento": v, "algoritmo": data[0] & 7,
                       "feedback": (data[0] >> 3) & 7, "bytes": data.hex(" ")})

for name, rows in (("smps_songs.csv", songs), ("smps_voices.csv", voices)):
    with open(out / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
print(len(songs), "músicas;", len(voices), "instrumentos FM")
