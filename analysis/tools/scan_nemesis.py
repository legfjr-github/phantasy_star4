"""Varre a ROM em busca de fluxos Nemesis válidos, inclusive os carregados por tabelas de ponteiros.

Filtro: cabeçalho com 1-1024 tiles, tabela de códigos bem formada (códigos de 1-8 bits, sem conflito
de prefixo) e decodificação completa sem erro. Os fluxos aceitos não se sobrepõem: após um acerto,
a varredura salta para o fim dele. Saída em assets/nemesis_scan/ e index.csv.
Opcional: scan_nemesis.py <pasta-do-despejo> para marcar quantos tiles batem com aquela VRAM.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sega_codecs import nemesis  # noqa: E402

here = Path(__file__).resolve().parent.parent
rom = (here / "ps4.bin").read_bytes()
out = here / "assets" / "nemesis_scan"
out.mkdir(parents=True, exist_ok=True)

vram_tiles = set()
if len(sys.argv) > 1:
    v = (Path(sys.argv[1]) / "vram.bin").read_bytes()
    v = bytes(b for i in range(0, len(v), 2) for b in (v[i + 1], v[i]))
    vram_tiles = {v[i:i + 32] for i in range(0, len(v), 32)} - {bytes(32)}


def table_ok(p):
    """Confere a tabela de códigos sem decodificar; devolve o fim dela ou None."""
    seen = []
    q = p + 2
    if rom[q] & 0x80 == 0:
        return None
    while q < len(rom) - 2:
        b = rom[q]
        q += 1
        if b == 0xFF:
            return q if len(seen) >= 2 else None
        if b & 0x80:
            continue
        length, code = b & 0x0F, rom[q]
        q += 1
        if not 1 <= length <= 8 or code >> length:
            return None
        for l2, c2 in seen:
            short, long_, ls, ll = (code, c2, length, l2) if length <= l2 else (c2, code, l2, length)
            if long_ >> (ll - ls) == short:
                return None
        seen.append((length, code))
        if len(seen) > 64:
            return None
    return None


rows = []
p = 0x80000
while p < len(rom) - 8:
    tiles = (rom[p] << 8 | rom[p + 1]) & 0x7FFF
    if 1 <= tiles <= 1024 and table_ok(p):
        try:
            data, used = nemesis(rom, p)
        except (ValueError, IndexError):
            data = None
        if data and used > 8 and len(data) / used > 1.05:
            ts = [data[i:i + 32] for i in range(0, len(data), 32)]
            hits = sum(t in vram_tiles for t in ts if t != bytes(32))
            name = f"nem_{p:06X}.bin"
            (out / name).write_bytes(data)
            rows.append({"rom": f"{p:06X}", "tiles": tiles, "packed": used, "vram_hits": hits})
            p += used + (used & 1)
            continue
    p += 2

with open(out / "index.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["rom", "tiles", "packed", "vram_hits"])
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} fluxos, {sum(r['tiles'] for r in rows)} tiles; melhores na VRAM:")
for r in sorted(rows, key=lambda r: -r["vram_hits"])[:10]:
    print(r)
