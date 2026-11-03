"""Procura blocos de texto comprimidos em Kosinski: tenta descomprimir em cada endereço da faixa
e aceita a saída quando 85%+ dos bytes são texto, 8%+ são espaços e menos de 1% fica fora da
codificação. Na ROM USA isso dá 43 blocos contíguos em 1DF5CA-1FD7A0.
Uso: scan_kosinski_text.py [inicio] [fim]   (hex; padrão 0D0000-200000)
Saída: assets/text/kosinski_text.csv (endereço, tamanhos) e os blocos em assets/text/blocks/.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sega_codecs import kosinski  # noqa: E402

here = Path(__file__).resolve().parent.parent
rom = (here / "ps4.bin").read_bytes()
start = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x0D0000
end = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x200000
out = here / "assets" / "text" / "blocks"
out.mkdir(parents=True, exist_ok=True)
TEXT = set(range(0x00, 0x3F)) | set(range(0xF0, 0x100))


def safe_kosinski(p, cap=0x10000):
    """Kosinski com limites, para abortar cedo em dados que não são Kosinski."""
    try:
        data, used = kosinski(rom, p)
    except (IndexError, ValueError):
        return None, 0
    return (data, used) if 16 <= len(data) <= cap else (None, 0)


rows = []
p = start
while p < end:
    data, used = safe_kosinski(p)
    # Texto real: ~13% de espaços e quase nenhum byte fora da codificação (gráficos passam no
    # primeiro filtro, mas não têm espaços).
    if (data and sum(b in TEXT for b in data) / len(data) >= 0.85
            and sum(0x1B <= b <= 0x34 for b in data) / len(data) >= 0.35
            and data.count(0) / len(data) >= 0.08
            and sum(0x3D <= b <= 0xEF for b in data) / len(data) < 0.01):
        (out / f"kos_{p:06X}.bin").write_bytes(data)
        rows.append({"rom": f"{p:06X}", "packed": used, "unpacked": len(data)})
        p += used
        continue
    p += 1

with open(here / "assets" / "text" / "kosinski_text.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["rom", "packed", "unpacked"])
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} blocos, {sum(r['unpacked'] for r in rows)} bytes de texto")
for r in rows[:15]:
    print(r)
