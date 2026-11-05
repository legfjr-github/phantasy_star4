"""Converte os VGMs gravados (YM2612 + SN76489) em MIDI, uma trilha por canal.

FM: frequência pelos registradores A4/A0 (+canal, porta 1 para os canais 4-6), nota ligada/desligada
pelo registrador 0x28 (bits 4-7 = operadores, bits 0-2 = canal). PSG: canais de tom 0-2, nota
desligada quando o volume é 0xF. DAC (bateria em PCM, registrador 0x2B ligado): cada início de
trecho de escritas em 0x2A vira uma nota de percussão no canal 10. Os timbres não são convertidos.
Uso: vgm2mid.py [pasta-de-vgm]   (padrão assets/sound/vgm; saída em assets/sound/midi)
"""
import math
import struct
import sys
from pathlib import Path

snd = Path(__file__).resolve().parent.parent / "assets" / "sound"
src = Path(sys.argv[1]) if len(sys.argv) > 1 else snd / "vgm"
dst = snd / "midi"
dst.mkdir(parents=True, exist_ok=True)
YM_CLOCK, PSG_CLOCK = 7670453, 3579545
TICKS = 480                       # por semínima, a 120 bpm: 960 ticks por segundo


def freq_to_note(f):
    return None if f <= 0 else max(0, min(127, round(69 + 12 * math.log2(f / 440))))


def parse(path):
    d = path.read_bytes()
    p = 0x34 + struct.unpack_from("<I", d, 0x34)[0]
    t = 0
    while p < len(d):
        c = d[p]
        if c == 0x66:
            return
        if c in (0x52, 0x53):
            yield t, ("fm", c - 0x52, d[p + 1], d[p + 2])
            p += 3
        elif c == 0x50:
            yield t, ("psg", d[p + 1])
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
            return


def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(out))


def convert(path):
    events = {k: [] for k in range(10)}   # 0-5 FM, 6-8 PSG, 9 DAC
    fnum_hi = [0] * 6
    freq = [0.0] * 6
    on = [None] * 6
    psg_tone = [0] * 3
    psg_on = [None] * 3
    latch = 0
    dac_enabled, last_dac = False, -10 ** 9
    for t, ev in parse(path):
        tick = round(t / 44100 * 960)
        if ev[0] == "fm":
            _, port, reg, val = ev
            if 0xA4 <= reg <= 0xA6:
                fnum_hi[reg - 0xA4 + port * 3] = val
            elif 0xA0 <= reg <= 0xA2:
                ch = reg - 0xA0 + port * 3
                fnum = ((fnum_hi[ch] & 7) << 8) | val
                block = (fnum_hi[ch] >> 3) & 7
                freq[ch] = fnum * YM_CLOCK / 144 / (1 << (21 - block))
            elif port == 0 and reg == 0x28:
                ch = (val & 3) + (3 if val & 4 else 0)
                if ch > 5:
                    continue
                if on[ch] is not None:
                    events[ch].append((tick, 0x80 | ch, on[ch], 0))
                    on[ch] = None
                if val & 0xF0:
                    n = freq_to_note(freq[ch])
                    if n is not None:
                        events[ch].append((tick, 0x90 | ch, n, 100))
                        on[ch] = n
            elif port == 0 and reg == 0x2B:
                dac_enabled = bool(val & 0x80)
            elif port == 0 and reg == 0x2A and dac_enabled:
                if t - last_dac > 220:  # começo de um novo trecho de sample
                    events[9].append((tick, 0x99, 36, 110))
                    events[9].append((tick + 30, 0x89, 36, 0))
                last_dac = t
        else:
            b = ev[1]
            if b & 0x80:
                latch = (b >> 4) & 7
                ch, is_vol = latch >> 1, latch & 1
                if ch < 3 and not is_vol:
                    psg_tone[ch] = (psg_tone[ch] & 0x3F0) | (b & 0x0F)
                if ch < 3 and is_vol:
                    # O driver muda o volume a cada quadro (envelope): só fecha a nota no silêncio e
                    # só abre uma nova quando a altura muda ou o canal volta do silêncio.
                    vol = b & 0x0F
                    n = freq_to_note(PSG_CLOCK / (32 * psg_tone[ch])) if psg_tone[ch] and vol != 0x0F else None
                    if psg_on[ch] is not None and n != psg_on[ch]:
                        events[6 + ch].append((tick, 0x80 | (6 + ch), psg_on[ch], 0))
                        psg_on[ch] = None
                    if n is not None and psg_on[ch] is None:
                        events[6 + ch].append((tick, 0x90 | (6 + ch), n, 127 - vol * 8))
                        psg_on[ch] = n
            else:
                ch = latch >> 1
                if ch < 3 and not latch & 1:
                    psg_tone[ch] = (psg_tone[ch] & 0x0F) | ((b & 0x3F) << 4)
    tracks = []
    for k, evs in events.items():
        if not evs:
            continue
        evs.sort(key=lambda x: x[0])
        body, last = bytearray(), 0
        name = (f"FM {k + 1}" if k < 6 else f"PSG {k - 5}" if k < 9 else "DAC").encode()
        body += b"\x00\xff\x03" + vlq(len(name)) + name
        for tick, st, n, vel in evs:
            body += vlq(tick - last) + bytes((st, n, vel))
            last = tick
        body += b"\x00\xff\x2f\x00"
        tracks.append(b"MTrk" + struct.pack(">I", len(body)) + bytes(body))
    tempo = b"\x00\xff\x51\x03\x07\xa1\x20\x00\xff\x2f\x00"  # 500000 us por semínima = 120 bpm
    tracks.insert(0, b"MTrk" + struct.pack(">I", len(tempo)) + tempo)
    hdr = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), TICKS)
    (dst / (path.stem + ".mid")).write_bytes(hdr + b"".join(tracks))
    return len(tracks) - 1


n = 0
for vgm in sorted(src.glob("ps4_*.vgm")):
    convert(vgm)
    n += 1
print(f"{n} MIDI em {dst}")
