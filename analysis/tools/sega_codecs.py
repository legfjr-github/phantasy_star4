"""Descompressores dos três formatos da Sega usados pelo PS4.

Cada função recebe a ROM inteira e o endereço inicial, e devolve (dados, bytes_consumidos).
Os algoritmos seguem as rotinas da ROM: Kosinski em 0x41BEA, Enigma em 0x41A90,
Nemesis em 0x41752 (para RAM) e 0x41740 (direto para o VDP).
"""


def kosinski(data, p):
    start = p
    out = bytearray()
    desc = data[p] | data[p + 1] << 8
    p += 2
    left = 16

    def bit():
        # A rotina pega o bit e só recarrega o campo depois de usar o 16º.
        nonlocal desc, left, p
        b = desc & 1
        desc >>= 1
        left -= 1
        if left == 0:
            desc = data[p] | data[p + 1] << 8
            p += 2
            left = 16
        return b

    while True:
        if bit():
            out.append(data[p])
            p += 1
            continue
        if bit():
            lo, hi = data[p], data[p + 1]
            p += 2
            offset = -0x2000 + (((hi & 0xF8) << 5) | lo)
            count = hi & 7
            if count:
                count += 2
            else:
                count = data[p]
                p += 1
                if count == 0:
                    break
                if count == 1:
                    continue
                count += 1
        else:
            count = (bit() << 1 | bit()) + 2
            offset = data[p] - 0x100
            p += 1
        for _ in range(count):
            out.append(out[len(out) + offset])
    return bytes(out), p - start


class BitReader:
    """Leitura MSB primeiro, como no Nemesis e no Enigma."""

    def __init__(self, data, p):
        self.data, self.p, self.buf, self.n = data, p, 0, 0

    def read(self, k):
        while self.n < k:
            self.buf = self.buf << 8 | self.data[self.p]
            self.p += 1
            self.n += 8
        self.n -= k
        return (self.buf >> self.n) & ((1 << k) - 1)


def nemesis(data, p):
    start = p
    header = data[p] << 8 | data[p + 1]
    p += 2
    xor_mode, tiles = header & 0x8000, header & 0x7FFF

    # Tabela de códigos: byte >= 0x80 define o nibble atual; senão (repetições<<4 | tamanho) seguido do código.
    codes = {}
    nibble = 0
    b = data[p]
    p += 1
    while b != 0xFF:
        if b & 0x80:
            nibble = b & 0x0F
            b = data[p]
            p += 1
            continue
        length, repeat = b & 0x0F, ((b >> 4) & 7) + 1
        codes[(length, data[p])] = (nibble, repeat)
        p += 1
        b = data[p]
        p += 1

    bits = BitReader(data, p)
    nibbles_needed = tiles * 64
    nibbles = []
    while len(nibbles) < nibbles_needed:
        code, length = 0, 0
        while True:
            code = code << 1 | bits.read(1)
            length += 1
            if length == 6 and code == 0b111111:
                repeat = bits.read(3) + 1
                nib = bits.read(4)
                break
            if (length, code) in codes:
                nib, repeat = codes[(length, code)]
                break
            if length > 8:
                raise ValueError(f"código Nemesis inválido em {bits.p:06X}")
        nibbles.extend([nib] * repeat)
    nibbles = nibbles[:nibbles_needed]

    out = bytearray()
    prev = 0
    for row in range(tiles * 8):
        v = 0
        for n in nibbles[row * 8:row * 8 + 8]:
            v = v << 4 | n
        if xor_mode:
            v ^= prev
            prev = v
        out += v.to_bytes(4, "big")
    return bytes(out), bits.p - start


def enigma(data, p, base=0):
    start = p
    inline_bits, mask = data[p], data[p + 1]
    inc = ((data[p + 2] << 8 | data[p + 3]) + base) & 0xFFFF
    lit = ((data[p + 4] << 8 | data[p + 5]) + base) & 0xFFFF
    bits = BitReader(data, p + 6)
    flag_bits = [(0x10, 0x8000), (0x08, 0x4000), (0x04, 0x2000), (0x02, 0x1000), (0x01, 0x0800)]
    out = []

    def inline():
        v = 0
        for m, f in flag_bits:
            if mask & m and bits.read(1):
                v |= f
        return v | bits.read(inline_bits)

    while True:
        if bits.read(1) == 0:
            kind = bits.read(1)
            count = bits.read(4) + 1
            for _ in range(count):
                if kind == 0:
                    out.append(inc)
                    inc = (inc + 1) & 0xFFFF
                else:
                    out.append(lit)
            continue
        kind = bits.read(2)
        count = bits.read(4)
        if kind == 3:
            if count == 15:
                break
            out.extend(inline() for _ in range(count + 1))
            continue
        v = inline()
        for _ in range(count + 1):
            out.append(v)
            v = (v + (1 if kind == 1 else -1 if kind == 2 else 0)) & 0xFFFF
    return b"".join(x.to_bytes(2, "big") for x in out), bits.p - start
