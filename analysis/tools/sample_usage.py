"""Uso dos samples PCM nas músicas, lido das trilhas de DAC (formato SMPS, ver export_smps.py).

Na trilha de DAC, EE n escolhe o sample (n = 1..17 -> sample_81..sample_91) e cada nota 81-DF vira o
"caso de taxa" do driver Z80 (tabela de salto Z80:0170), cuja taxa foi medida no emulador
(assets/sound/dac_rate_cases.csv). Grava assets/sound/sample_usage.csv e reescreve os WAV de cada
sample com a taxa mais usada nas músicas.
"""
import csv
import struct
from collections import Counter, defaultdict
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
snd = root / "assets" / "sound"
ARGS = {0xE0: 1, 0xE1: 1, 0xE2: 1, 0xE3: 1, 0xE4: 1, 0xE5: 2, 0xE6: 1, 0xE7: 0, 0xE8: 1, 0xE9: 2,
        0xEA: 1, 0xEB: 1, 0xEC: 1, 0xED: 1, 0xEE: 1, 0xEF: 1, 0xF0: 4, 0xF1: 2, 0xF2: 0, 0xF3: 1,
        0xF4: 1, 0xF5: 1, 0xF6: 2, 0xF7: 4, 0xF8: 2, 0xF9: 0, 0xFA: 1, 0xFB: 1, 0xFC: 1, 0xFD: 1,
        0xFE: 1, 0xFF: 1}
rates = {int(r["caso"], 16): int(r["taxa_hz"]) for r in csv.DictReader(open(snd / "dac_rate_cases.csv", encoding="utf-8"))
         if r["taxa_hz"]}

cases = defaultdict(Counter)
songs = defaultdict(set)
for sid in range(0x81, 0xB5):
    h = struct.unpack_from(">I", rom, 0xD1C40 + (sid - 0x81) * 4)[0]
    q = h + struct.unpack_from(">H", rom, h + 6)[0]  # trilha 0 = DAC
    # Executa a trilha como o driver: F8 chama e F9 retorna (pilha), F7 repete, F6 salta (fim da
    # passada, pois a música volta ao laço) e F2 encerra. Destino = endereço do 2º byte + deslocamento.
    sample, steps, stack, loops = None, 0, [], {}
    while steps < 20000:
        b = rom[q]
        q += 1
        steps += 1
        if b == 0xEE:
            n = rom[q]
            sample = 0x80 + n if 1 <= n <= 17 else None
        if 0x81 <= b <= 0xDF and sample:
            cases[sample][b] += 1
            songs[sample].add(f"{sid:02X}")
        if b < 0xE0:
            continue
        if b in (0xF2, 0xF6):
            break
        if b == 0xF8:
            stack.append(q + 2)
            q = q + 1 + struct.unpack_from(">h", rom, q)[0]
            continue
        if b == 0xF9:
            if not stack:
                break
            q = stack.pop()
            continue
        if b == 0xF7:
            idx, count = rom[q], rom[q + 1]
            left = loops.get((q, idx), count) - 1
            if left > 0:
                loops[(q, idx)] = left
                q = q + 3 + struct.unpack_from(">h", rom, q + 2)[0]
            else:
                loops.pop((q, idx), None)
                q += 4
            continue
        q += ARGS[b]

rows = []
for s in range(0x81, 0x92):
    c = cases.get(s, Counter())
    top = c.most_common(1)[0][0] if c else None
    rate = rates.get(top) if top else None
    rows.append({"sample": f"sample_{s:02X}", "musicas": " ".join(sorted(songs.get(s, []))),
                 "casos_de_taxa": " ".join(f"{k:02X}({rates.get(k, '?')}Hz)x{v}" for k, v in c.most_common(6)),
                 "taxa_mais_usada_hz": rate or ""})
    wav = snd / f"sample_{s:02X}.wav"
    if rate and wav.exists():
        pcm = wav.read_bytes()[44:]
        hdr = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16, 1, 1, rate, rate, 1, 8,
                          b"data", len(pcm))
        wav.write_bytes(hdr + pcm)
with open(snd / "sample_usage.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r["sample"], r["taxa_mais_usada_hz"], "|", r["casos_de_taxa"][:70], "|", r["musicas"][:40])
