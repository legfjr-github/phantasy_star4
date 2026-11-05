"""Peças comuns de enemy_gallery.py e party_battle.py: achar um encontro, repeti-lo e ler o plano A."""
import random
import struct

from ps4emu import Emu, C, B, UP, DOWN, LEFT, RIGHT

MAP = 0x15  # masmorra com zona de encontro 14


def do_step(e, step):
    e.run(*step)
    e.press(B, 3, 8)


def setup(preload):
    """Entra na masmorra pelo patch da abertura e anda ao acaso, guardando um estado antes de cada
    passo, até Battle_LoadEnemy (0x7F5E) executar. Devolve (emulador, estado, passo): o emulador é
    determinístico, então carregar o estado e repetir o passo repete o encontro."""
    e = Emu()
    e.load_state(preload)
    e.patch_rom(0x73E34, MAP.to_bytes(2, "big"))
    e.press(C, 3, 20)
    for _ in range(40):
        e.press(B, 3, 15)
    rng = random.Random(1)
    for _ in range(2000):
        st = e.save_state()
        step = (rng.randint(20, 80), rng.choice((UP, DOWN, LEFT, RIGHT)))
        e.trace(True)
        do_step(e, step)
        if e.executed(0x7F5E):
            return e, st, step
    raise RuntimeError("nenhum encontro")


def plane_a(e, keep):
    """Desenha o plano A (0xC000, 64x32 células) com fundo transparente, só as células em que
    keep(tile, linha) é verdadeiro. Devolve (largura, altura, RGBA, células usadas)."""
    vram, cram = e.vram(), bytes(e.mem(1))
    pal = []
    for i in range(64):
        v = struct.unpack_from("<H", cram, i * 2)[0]  # formato do núcleo: 0000 000B BBGG GRRR
        r, g, b = v & 7, (v >> 3) & 7, (v >> 6) & 7
        pal.append(bytes((r * 255 // 7, g * 255 // 7, b * 255 // 7, 255)))
    W, H = 512, 256
    img = bytearray(W * H * 4)
    used = []
    for cy in range(32):
        for cx in range(64):
            ent = struct.unpack_from(">H", vram, 0xC000 + (cy * 64 + cx) * 2)[0]
            t, p, hf, vf = ent & 0x7FF, (ent >> 13) & 3, ent & 0x800, ent & 0x1000
            if not keep(t, cy):
                continue
            used.append((cx, cy))
            for py in range(8):
                row = vram[t * 32 + (7 - py if vf else py) * 4:][:4]
                for px in range(8):
                    sx = 7 - px if hf else px
                    c = (row[sx >> 1] >> (0 if sx & 1 else 4)) & 15
                    if c:
                        o = ((cy * 8 + py) * W + cx * 8 + px) * 4
                        img[o:o + 4] = pal[p * 16 + c]
    return W, H, img, used


def crop(W, img, cells):
    x0, x1 = min(c[0] for c in cells) * 8, (max(c[0] for c in cells) + 1) * 8
    y0, y1 = min(c[1] for c in cells) * 8, (max(c[1] for c in cells) + 1) * 8
    return x1 - x0, y1 - y0, b"".join(img[(y * W + x0) * 4:(y * W + x1) * 4] for y in range(y0, y1))
