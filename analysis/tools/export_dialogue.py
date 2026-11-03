"""Gera assets/text/dialogue.txt com todo o diálogo encontrado.

1) Blocos Kosinski listados em kosinski_text.csv (scan_kosinski_text.py).
2) Mensagens não comprimidas do banco de texto, entre o fim do último bloco Kosinski e 0x200000
   (ali fica a tabela "não tem nada aqui", 1FE650). Fora dessa faixa, a varredura só achava
   gráficos que por acaso pareciam texto.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from text_codec import END, messages  # noqa: E402

here = Path(__file__).resolve().parent.parent
rom = (here / "ps4.bin").read_bytes()
text_dir = here / "assets" / "text"

blocks = []
with open(text_dir / "kosinski_text.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        a = int(r["rom"], 16)
        blocks.append((a, a + int(r["packed"])))

lines, n_msgs = [], 0
for a, _ in blocks:
    data = (text_dir / "blocks" / f"kos_{a:06X}.bin").read_bytes()
    lines.append(f"######## bloco Kosinski {a:06X} ({len(data)} bytes)")
    for off, text in messages(data):
        if text.strip():
            lines.append(f"-- {a:06X}+{off:04X}\n{text}")
            n_msgs += 1


def plain_ok(text):
    letters = [c for c in text if c.isalpha()]
    return ("{" not in text.replace("{page}", "").replace("{face:", "").replace("{ask}", "")
            and text.count(" ") >= 2 and letters and sum(c.islower() for c in letters) / len(letters) >= 0.6)


in_block = lambda p: any(s <= p < e for s, e in blocks)  # noqa: E731
lines.append("######## mensagens sem compressão")
p, n_plain = max(e for _, e in blocks), 0
while p < 0x200000:
    end = next((q for q in range(p, min(p + 600, len(rom))) if rom[q] in END), None)
    if end is None or in_block(p):
        p += 1
        continue
    msgs = messages(rom[p:end + 1])
    text = msgs[0][1] if msgs else ""
    if len(text) >= 8 and plain_ok(text):
        lines.append(f"-- {p:06X}\n{text}")
        n_plain += 1
        p = end + 1
    else:
        p += 1

(text_dir / "dialogue.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{len(blocks)} blocos Kosinski, {n_msgs} mensagens; {n_plain} mensagens sem compressão")
