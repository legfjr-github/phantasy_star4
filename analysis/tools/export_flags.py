"""Mapa das flags de evento: quem testa, liga e desliga cada uma (código e diálogo).

Bancos de 256 bits na RAM, bit 7 primeiro (0x5764A/0x5768C):
  FFF100 história, FFF120 e FFF140 (o código de baú escolhe o banco por FFECC3), FFF160.
Rotinas, com o número da flag em D0: testar 0x57624/0x5762E/0x57638, ligar 0x57666/0x57670/
0x5767A/0x57684, e as de 0x576A8 em diante (mesma estrutura) apagam.
No texto, FA <flag> <n> testa a flag no banco FFF100 e pula n mensagens se ela estiver ligada.
Lê export/listing.asm (ExportAllMD.java) e assets/text/blocks; grava assets/data/flags.csv.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from text_codec import messages  # noqa: E402

here = Path(__file__).resolve().parent.parent
listing = (here / "export" / "listing.asm").read_text(encoding="utf-8").splitlines()
ROUTINES = {
    "00057624": ("testa", "F100"), "0005762e": ("testa", "F120"), "00057638": ("testa", "F140"),
    "00057666": ("liga", "F100"), "00057670": ("liga", "F120"), "0005767a": ("liga", "F140"),
    "00057684": ("liga", "F160"),
}
LOAD = re.compile(r"(?:moveq|move\.[bw]) #?(-?0x[0-9a-f]+|\d+),D0[bw]?$")

uses = defaultdict(lambda: defaultdict(list))
unknown = 0
func = ""
for k, line in enumerate(listing):
    if line.startswith("; ==== "):
        func = line[7:].split(" @ ")[0]
    m = re.search(r"\s([0-9a-f]{8})\s+(?:jsr|bsr\.[bw]|jmp)\s+0x([0-9a-f]{8})", line)
    if not m or m.group(2) not in ROUTINES:
        continue
    kind, bank = ROUTINES[m.group(2)]
    flag = None
    for back in listing[max(0, k - 6):k][::-1]:
        lm = LOAD.search(back.strip())
        if lm:
            flag = int(lm.group(1), 16 if "x" in lm.group(1) else 10) & 0xFF
            break
        if "D0" in back.split()[-1] if back.split() else False:
            break
    if flag is None:
        unknown += 1
        continue
    uses[(bank, flag)][kind].append(f"{m.group(1)[2:]}({func})")

for f in sorted((here / "assets" / "text" / "blocks").glob("kos_*.bin")):
    block = f.stem[4:]
    for off, text in messages(f.read_bytes()):
        for fm in re.finditer(r"\{if:([0-9A-F]{2})([0-9A-F]{2})\}", text):
            uses[("F100", int(fm.group(1), 16))]["texto"].append(f"{block}+{off:04X}")

rows = [{"banco": f"FF{bank}", "flag": f"{flag:02X}",
         "liga": " ".join(v["liga"]), "testa_codigo": " ".join(v["testa"]),
         "testa_texto": " ".join(v["texto"][:12]) + (" ..." if len(v["texto"]) > 12 else "")}
        for (bank, flag), v in sorted(uses.items())]
out = here / "assets" / "data"
out.mkdir(parents=True, exist_ok=True)
with open(out / "flags.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} flags; {unknown} chamadas com a flag em registrador (não resolvidas estaticamente)")
