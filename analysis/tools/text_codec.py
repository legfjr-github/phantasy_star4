"""Codificação de texto do diálogo (interpretador em 0x6A090).

0x00 espaço, 0x01-0x1A A-Z, 0x1B-0x34 a-z, pontuação em PUNCT, bytes >= 0xF0 são controles
com o número de bytes de argumento em CONTROL. Uma mensagem termina em F7 ou FF.
"""

PUNCT = {0x00: " ", 0x35: ".", 0x36: "'", 0x37: ",", 0x39: ":", 0x3A: "!", 0x3B: "?", 0x3C: "-"}
PUNCT.update({0x40 + d: str(d) for d in range(10)})  # "500 meseta" = 45 40 40
CONTROL = {0xF0: ("F0", 0), 0xF1: ("F1", 0), 0xF2: ("call", 1), 0xF3: ("F3", 0), 0xF4: ("face", 1),
           0xF5: ("ask", 0), 0xF6: ("F6", 2), 0xF8: ("F8", 0), 0xF9: ("wait", 1), 0xFA: ("if", 2),
           0xFB: ("FB", 0), 0xFC: ("\n", 0), 0xFD: ("page", 0), 0xFE: ("FE", 0)}
# F2 <sub> chama a sub-rotina <sub> da tabela em 0x6A550; algumas leem mais bytes.
CALL_EXTRA = {0x00: 2, 0x03: 1, 0x04: 1}
END = (0xF7, 0xFF)


def messages(data):
    """Divide um bloco descomprimido em mensagens; devolve [(offset, texto)]."""
    out, s, start, p = [], [], 0, 0
    while p < len(data):
        b = data[p]
        p += 1
        if b in END:
            out.append((start, "".join(s)))
            s, start = [], p
        elif 1 <= b <= 26:
            s.append(chr(64 + b))
        elif 0x1B <= b <= 0x34:
            s.append(chr(97 + b - 0x1B))
        elif b in PUNCT:
            s.append(PUNCT[b])
        elif b in CONTROL:
            name, n = CONTROL[b]
            if b == 0xF2 and p < len(data):
                n += CALL_EXTRA.get(data[p], 0)
            args = data[p:p + n]
            p += n
            s.append("\n" if name == "\n" else "{" + name + (":" + args.hex().upper() if n else "") + "}")
        else:
            s.append("{%02X}" % b)
    if s:
        out.append((start, "".join(s)))
    return out
