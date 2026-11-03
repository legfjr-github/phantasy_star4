"""Extrai as listas de nomes não comprimidas (itens, técnicas, classes, monstros, lugares).

Codificação observada nas tabelas: 0x01-0x1A = A-Z (a fonte em 0x2A303A só tem maiúsculas),
0x31 aparece entre palavras ("LACO?AXE"), e FE/FF terminam cada nome.
Uma lista é aceita com 4+ nomes seguidos de 3+ letras. Saída: assets/text/name_tables.txt
"""
from pathlib import Path

here = Path(__file__).resolve().parent.parent
rom = (here / "ps4.bin").read_bytes()
out = here / "assets" / "text"
out.mkdir(parents=True, exist_ok=True)

SPECIAL = {0x31: " "}


def word_at(p):
    """Devolve (texto, fim) se em p começa um nome válido terminado por FE/FF."""
    s = []
    q = p
    while q < len(rom) and len(s) < 24:
        b = rom[q]
        if b in (0xFE, 0xFF):
            return ("".join(s), q + 1) if len(s) >= 3 and s[0] != " " else (None, q + 1)
        if 1 <= b <= 26:
            s.append(chr(64 + b))
        elif b in SPECIAL:
            s.append(SPECIAL[b])
        else:
            return None, q + 1
        q += 1
    return None, q


lines = []
p = 0x80000
while p < len(rom):
    names, q = [], p
    while True:
        w, end = word_at(q)
        if w is None:
            break
        names.append(w)
        q = end
    if len(names) >= 4:
        lines.append(f"== {p:06X} ({len(names)} nomes)")
        lines.extend(f"  {n}" for n in names)
        p = q
    else:
        p += 1

(out / "name_tables.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(l for l in lines if l.startswith("==")))
