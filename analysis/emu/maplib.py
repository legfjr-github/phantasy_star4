"""Composição de mapas de campo: blocos de 4x4 tiles, camada de baixo opaca e de cima com cor 0 transparente."""
import struct


def compose(vram, palette_words, blocks, layers, w, h, stride):
    """palette_words: 64 cores no formato do hardware (0000BBB0GGG0RRR0). Devolve (W, H, RGBA)."""
    pal = []
    for c in palette_words:
        r, g, b = (c >> 1) & 7, (c >> 5) & 7, (c >> 9) & 7
        pal.append(bytes((r * 255 // 7, g * 255 // 7, b * 255 // 7, 255)))
    W, H = w * 32, h * 32
    img = bytearray(W * H * 4)
    cache = {}

    def tile_rows(ent):
        """8 linhas RGBA de um tile (com paleta e espelhamento) e os índices de cor de cada linha."""
        key = ent & 0x7FFF
        if key not in cache:
            t, p = (ent & 0x7FF) * 32, (ent >> 13) & 3
            hf, vf = ent & 0x800, ent & 0x1000
            rows = []
            for y in range(8):
                src = vram[t + (7 - y if vf else y) * 4:][:4]
                idx = [(src[(7 - x if hf else x) >> 1] >> (0 if (7 - x if hf else x) & 1 else 4)) & 15
                       for x in range(8)]
                rows.append((b"".join(pal[p * 16 + c] for c in idx), idx))
            cache[key] = rows
        return cache[key]

    for layer_index, layout in enumerate(layers):
        for by in range(h):
            for bx in range(w):
                b = layout[by * stride + bx]
                if b * 32 + 32 > len(blocks):
                    continue
                for k, ent in enumerate(struct.unpack_from(">16H", blocks, b * 32)):
                    ox, oy = bx * 32 + (k % 4) * 8, by * 32 + (k // 4) * 8
                    for y, (rgba, idx) in enumerate(tile_rows(ent)):
                        o = ((oy + y) * W + ox) * 4
                        if layer_index == 0:
                            img[o:o + 32] = rgba
                        else:
                            for x, c in enumerate(idx):
                                if c:
                                    img[o + x * 4:o + x * 4 + 4] = rgba[x * 4:x * 4 + 4]
    return W, H, bytes(img)
