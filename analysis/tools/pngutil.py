"""Gravação de PNG RGBA sem bibliotecas externas."""
import struct
import zlib
from pathlib import Path


def png(path, w, h, rgba):
    raw = b"".join(b"\x00" + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


GRAY = [bytes((v, v, v, 255)) for v in (i * 17 for i in range(16))]


def cram_palette(cram, line):
    """Linha (0-3) de 16 cores de um cram.bin despejado pelo app (9 bits BBBGGGRRR, little-endian)."""
    out = []
    for i in range(16):
        v = struct.unpack_from("<H", cram, (line * 16 + i) * 2)[0]
        out.append(bytes(((v & 7) * 255 // 7, ((v >> 3) & 7) * 255 // 7, ((v >> 6) & 7) * 255 // 7, 255)))
    return out


def tiles_png(path, data, palette=GRAY, cols=16):
    """Folha de tiles 8x8 de 4 bits, `cols` por linha."""
    n = len(data) // 32
    rows = max(1, (n + cols - 1) // cols)
    img = bytearray(cols * 8 * rows * 8 * 4)
    for t in range(n):
        for i in range(64):
            c = (data[t * 32 + i // 2] >> (4 if i % 2 == 0 else 0)) & 15
            o = (((t // cols) * 8 + i // 8) * cols * 8 + (t % cols) * 8 + i % 8) * 4
            img[o:o + 4] = palette[c]
    png(path, cols * 8, rows * 8, bytes(img))
