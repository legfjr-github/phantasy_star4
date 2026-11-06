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


def plane_a(e, keep, vram=None, cram=None):
    """Desenha o plano A (0xC000, 64x32 células) com fundo transparente, só as células em que
    keep(tile, linha) é verdadeiro. Devolve (largura, altura, RGBA, células usadas).
    vram/cram permitem usar cópias tiradas em quadros diferentes."""
    vram = vram if vram is not None else e.vram()
    cram = cram if cram is not None else bytes(e.mem(1))
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


def snapshot(e):
    """Cópia do que o VDP precisa para redesenhar o quadro (VRAM, registradores, VSRAM, CRAM) e da tela."""
    wh = e.lib.ps_frame_size()
    return {"vram": e.vram(), "reg": bytes(e.mem(3)), "vsram": bytes(e.mem(2)), "cram": bytes(e.mem(1)),
            "frame": bytes(e.mem(6)), "size": (wh >> 16, wh & 0xFFFF)}


def save_frame(snap, path):
    """Grava a tela guardada no snapshot (RGB565 do núcleo) como PNG."""
    from pngutil import png
    w, h = snap["size"]
    raw = snap["frame"]
    img = bytearray(w * h * 4)
    for i in range(w * h):
        v = raw[i * 2] | raw[i * 2 + 1] << 8
        img[i * 4:i * 4 + 4] = bytes((((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63,
                                      (v & 31) * 255 // 31, 255))
    png(path, w, h, bytes(img))


def _layers(snap):
    v, reg = snap["vram"], snap["reg"]
    pa, pb = (reg[2] & 0x38) << 10, (reg[4] & 7) << 13
    pw = {0: 32, 1: 64, 3: 128}[reg[16] & 3]
    ph = {0: 32, 1: 64, 3: 128}[(reg[16] >> 4) & 3]
    hs = (reg[13] & 0x3F) << 10
    hs_a, hs_b = struct.unpack_from(">hh", v, hs)
    vs_a, vs_b = struct.unpack_from("<hh", snap["vsram"], 0)  # VSRAM do núcleo em little-endian
    return v, reg, ((pb, hs_b, vs_b), (pa, hs_a, vs_a)), pw, ph


def enemy_tiles(snap, lo, hi, sprites=True):
    """Quantos tiles da faixa [lo, hi) aparecem nos planos B e A (e nos sprites, se sprites)."""
    v, reg, planes, pw, ph = _layers(snap)
    n = 0
    for base, _, _ in planes:
        for i in range(pw * ph):
            if lo <= (struct.unpack_from(">H", v, base + i * 2)[0] & 0x7FF) < hi:
                n += 1
    if not sprites:
        return n
    sat, link = (reg[5] & 0x7F) << 9, 0
    for _ in range(80):
        _, size, lk, attr, _ = struct.unpack_from(">HBBHH", v, sat + link * 8)
        if lo <= (attr & 0x7FF) < hi:
            n += (((size >> 2) & 3) + 1) * ((size & 3) + 1)
        link = lk & 0x7F
        if not link:
            break
    return n


def min_plane_tile(snap, lo, hi):
    """Menor tile da faixa [lo, hi) usado nos planos A e B (início dos tiles do inimigo)."""
    v, reg, planes, pw, ph = _layers(snap)
    ts = [struct.unpack_from(">H", v, base + i * 2)[0] & 0x7FF for base, _, _ in planes for i in range(pw * ph)]
    ts = [t for t in ts if lo <= t < hi]
    return min(ts) if ts else None


def enemy_image(snap, cram, lo, hi):
    """Desenha na posição da tela (320x224) só o que usa tiles da faixa [lo, hi): plano B, plano A
    (com a rolagem de cada um) e sprites por cima. Devolve (largura, altura, RGBA) recortado, ou None."""
    v, reg, planes, pw, ph = _layers(snap)
    pal = []
    for i in range(64):
        c = struct.unpack_from("<H", cram, i * 2)[0]
        pal.append(bytes(((c & 7) * 255 // 7, ((c >> 3) & 7) * 255 // 7, ((c >> 6) & 7) * 255 // 7, 255)))
    W, H = 320, 224
    img = bytearray(W * H * 4)

    def tile(t, p, hf, vf, sx0, sy0):
        for py in range(8):
            row = v[(t & 0x7FF) * 32 + (7 - py if vf else py) * 4:][:4]
            for px in range(8):
                x, y = sx0 + px, sy0 + py
                if not (0 <= x < W and 0 <= y < H):
                    continue
                s = 7 - px if hf else px
                c = (row[s >> 1] >> (0 if s & 1 else 4)) & 15
                if c:
                    img[(y * W + x) * 4:(y * W + x) * 4 + 4] = pal[p * 16 + c]

    for base, hs, vs in planes:
        for cy in range(ph):
            for cx in range(pw):
                ent = struct.unpack_from(">H", v, base + (cy * pw + cx) * 2)[0]
                if not lo <= (ent & 0x7FF) < hi:
                    continue
                sx = (cx * 8 + hs) % (pw * 8)
                sy = (cy * 8 - vs) % (ph * 8)
                sx -= pw * 8 if sx >= W + 8 else 0
                sy -= ph * 8 if sy >= H + 8 else 0
                tile(ent, (ent >> 13) & 3, ent & 0x800, ent & 0x1000, sx, sy)
    sat, link, order = (reg[5] & 0x7F) << 9, 0, []
    for _ in range(80):
        order.append(link)
        link = v[sat + link * 8 + 3] & 0x7F
        if not link:
            break
    for s in reversed(order):  # o primeiro da lista fica por cima
        y, size, _, attr, x = struct.unpack_from(">HBBHH", v, sat + s * 8)
        if not lo <= (attr & 0x7FF) < hi:
            continue
        w, h = ((size >> 2) & 3) + 1, (size & 3) + 1
        hf, vf = attr & 0x800, attr & 0x1000
        for tx in range(w):
            for ty in range(h):
                cx, cy = (w - 1 - tx) if hf else tx, (h - 1 - ty) if vf else ty
                tile((attr & 0x7FF) + tx * h + ty, (attr >> 13) & 3, hf, vf,
                     (x & 0x1FF) - 128 + cx * 8, (y & 0x3FF) - 128 + cy * 8)
    xs = [i % W for i in range(W * H) if img[i * 4 + 3]]
    if not xs:
        return None
    ys = [i // W for i in range(W * H) if img[i * 4 + 3]]
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    return x1 - x0, y1 - y0, b"".join(img[(y * W + x0) * 4:(y * W + x1) * 4] for y in range(y0, y1))


def crop(W, img, cells):
    x0, x1 = min(c[0] for c in cells) * 8, (max(c[0] for c in cells) + 1) * 8
    y0, y1 = min(c[1] for c in cells) * 8, (max(c[1] for c in cells) + 1) * 8
    return x1 - x0, y1 - y0, b"".join(img[(y * W + x0) * 4:(y * W + x1) * 4] for y in range(y0, y1))
