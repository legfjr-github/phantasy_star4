"""Mede a taxa real de cada sample PCM a partir dos VGMs gravados (assets/sound/vgm).

Pega as escritas no registrador 0x2A do YM2612 (dado do DAC), separa em trechos quando o intervalo
passa de 5 ms, casa cada trecho com um sample extraído (assets/sound/sample_*.wav) e mede o
intervalo mediano entre bytes. Grava assets/sound/sample_rates.csv e reescreve os WAV com a taxa medida.
"""
import csv
import statistics
import struct
from collections import defaultdict
from pathlib import Path

snd = Path(__file__).resolve().parent.parent / "assets" / "sound"
samples = {p.stem: p.read_bytes()[44:] for p in snd.glob("sample_*.wav")}


def dac_writes(vgm):
    d = vgm.read_bytes()
    p = 0x34 + struct.unpack_from("<I", d, 0x34)[0]
    t, out = 0, []
    while p < len(d):
        c = d[p]
        if c == 0x66:
            break
        if c in (0x52, 0x53):
            if c == 0x52 and d[p + 1] == 0x2A:
                out.append((t, d[p + 2]))
            p += 3
        elif c == 0x50:
            p += 2
        elif c == 0x61:
            t += struct.unpack_from("<H", d, p + 1)[0]
            p += 3
        elif c == 0x62:
            t += 735
            p += 1
        elif c == 0x63:
            t += 882
            p += 1
        elif 0x70 <= c <= 0x7F:
            t += c - 0x6F
            p += 1
        else:
            raise ValueError(f"comando VGM {c:02X} em {vgm.name}")
    return out


gaps = defaultdict(list)
for vgm in sorted((snd / "vgm").glob("*.vgm")):
    w = dac_writes(vgm)
    run = w[:1]
    for prev, cur in zip(w, w[1:]):
        if cur[0] - prev[0] <= 220:  # 5 ms a 44,1 kHz
            run.append(cur)
            continue
        if len(run) > 40:
            data = bytes(x[1] for x in run)
            # casa por várias janelas de 16 bytes (samples curtos ou interrompidos por outro sample)
            for name, pcm in samples.items():
                if any(data[k:k + 16] in pcm for k in range(8, min(len(data) - 16, 200), 24)
                       if len(set(data[k:k + 16])) > 3):
                    gaps[name].append((run[-1][0] - run[0][0]) / (len(run) - 1))
                    break
        run = [cur]

rows = []
for name in sorted(samples):
    if gaps[name]:
        rate = 44100 / statistics.median(gaps[name])
        rows.append({"sample": name, "taxa_hz": round(rate), "trechos_medidos": len(gaps[name])})
        pcm = samples[name]
        r = round(rate)
        hdr = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16, 1, 1, r, r, 1, 8,
                          b"data", len(pcm))
        (snd / f"{name}.wav").write_bytes(hdr + pcm)
    else:
        rows.append({"sample": name, "taxa_hz": "", "trechos_medidos": 0})
with open(snd / "sample_rates.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=rows[0].keys())
    wr.writeheader()
    wr.writerows(rows)
for r in rows:
    print(r)
