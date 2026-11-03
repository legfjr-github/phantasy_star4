"""Extrai os samples PCM tocados pelo driver Z80 (DAC do YM2612) como WAV 8 bits mono.

Tabela em Z80:0500 = (banco, índice) por sample, IDs 0x81 em diante.
Banco N aponta para ROM 0x0E0000 + bit0*0x8000 + bit1*0x10000 (o driver grava A15, A16 e 1,1,1 em A17-A19).
Cada banco abre com cabeçalhos de 8 bytes: início, tamanho, início do loop, tamanho do loop
(little-endian, endereços da janela Z80 8000-FFFF).
"""
import csv
import struct
import sys
from pathlib import Path

here = Path(__file__).resolve().parent.parent
rom = (here / "ps4.bin").read_bytes()
drv = (here / "z80" / "z80_driver.bin").read_bytes()
out = here / "assets" / "sound"
out.mkdir(parents=True, exist_ok=True)
rate = int(sys.argv[1]) if len(sys.argv) > 1 else 11025

rows, seen = [], set()
for sid in range((len(drv) - 0x500) // 2):
    bank, idx = drv[0x500 + sid * 2], drv[0x501 + sid * 2]
    base = 0x0E0000 + (bank & 1) * 0x8000 + ((bank >> 1) & 1) * 0x10000
    start, length, loop_start, loop_len = struct.unpack_from("<4H", rom, base + idx * 8)
    rom_start = base + start - 0x8000
    name = f"sample_{0x81 + sid:02X}.wav"
    ok = start >= 0x8000 and length > 0 and rom_start + length <= len(rom)
    if ok and (rom_start, length) not in seen:
        seen.add((rom_start, length))
        pcm = rom[rom_start:rom_start + length]
        header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + length, b"WAVE", b"fmt ", 16, 1, 1,
                             rate, rate, 1, 8, b"data", length)
        (out / name).write_bytes(header + pcm)
    rows.append({"id": f"{0x81 + sid:02X}", "bank": bank, "index": idx, "rom_start": f"{rom_start:06X}",
                 "length": length, "loop": f"{loop_start:04X}+{loop_len}" if loop_len else "",
                 "file": name if ok else ""})

with open(out / "samples.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r)
