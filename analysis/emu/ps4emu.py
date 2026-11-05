"""Controle do emulador (gpgx_pc.dll) pelo Python: quadros, entrada, memória, estados, tela e VGM."""
import ctypes
import struct
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "tools"))
from pngutil import png  # noqa: E402

# Bits do joypad (mapeamento Genesis Plus GX)
B, A, START, UP, DOWN, LEFT, RIGHT, C = 1, 2, 8, 16, 32, 64, 128, 256


class SoundWrite(ctypes.Structure):
    _fields_ = [("frame", ctypes.c_uint), ("cycles", ctypes.c_uint), ("kind", ctypes.c_ubyte),
                ("addr", ctypes.c_ubyte), ("data", ctypes.c_ubyte), ("pad", ctypes.c_ubyte)]


class Emu:
    MCLK_PER_FRAME = 3420 * 262  # NTSC

    def __init__(self, rom=None, dll="gpgx_pc.dll"):
        self.lib = ctypes.CDLL(str(here / dll))
        self.lib.ps_trace_marks.restype = ctypes.POINTER(ctypes.c_ubyte * 0x400000)
        self.lib.ps_watch_log.restype = ctypes.c_void_p
        self.lib.ps_rom.restype = ctypes.c_void_p
        self.lib.ps_mem.restype = ctypes.POINTER(ctypes.c_ubyte)
        self.lib.ps_log_buf.restype = ctypes.POINTER(SoundWrite)
        self.lib.ps_fps.restype = ctypes.c_double
        rom = rom or str(here.parent / "ps4.bin")
        if not self.lib.ps_load(rom.encode(), str(here).encode()):
            raise RuntimeError("ROM não carregou")

    def run(self, frames=1, mask=0):
        self.lib.ps_run(frames, mask)

    def press(self, mask, hold=4, release=8):
        self.run(hold, mask)
        self.run(release, 0)

    def mem(self, which):
        size = ctypes.c_int()
        p = self.lib.ps_mem(which, ctypes.byref(size))
        return ctypes.cast(p, ctypes.POINTER(ctypes.c_ubyte * size.value)).contents

    # O núcleo guarda VRAM e RAM do 68000 em palavras little-endian; estas funções corrigem.
    def ram(self):
        r = bytes(self.mem(4))
        return bytes(b for i in range(0, len(r), 2) for b in (r[i + 1], r[i]))

    def vram(self):
        r = bytes(self.mem(0))
        return bytes(b for i in range(0, len(r), 2) for b in (r[i + 1], r[i]))

    def poke(self, addr, value):
        """Grava um byte na RAM do 68000 (endereço FFxxxx ou xxxx)."""
        self.mem(4)[(addr & 0xFFFF) ^ 1] = value & 0xFF

    def peek(self, addr, size=1):
        r = self.mem(4)
        return int.from_bytes(bytes(r[((addr + i) & 0xFFFF) ^ 1] for i in range(size)), "big")

    def save_state(self):
        n = self.lib.ps_state_size()
        buf = ctypes.create_string_buffer(n)
        self.lib.ps_save_state(buf, n)
        return buf.raw

    def load_state(self, data):
        self.lib.ps_load_state(data, len(data))

    def screenshot(self, path):
        wh = self.lib.ps_frame_size()
        w, h = wh >> 16, wh & 0xFFFF
        raw = bytes(self.mem(6))
        img = bytearray(w * h * 4)
        for i in range(w * h):
            v = raw[i * 2] | raw[i * 2 + 1] << 8
            img[i * 4:i * 4 + 4] = bytes((((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63,
                                          (v & 31) * 255 // 31, 255))
        png(path, w, h, bytes(img))

    def dump_vdp(self, folder):
        """Mesmo formato do "Exportar gráficos" do app (lido por tools/render_vdp.py)."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        for name, which in (("vram", 0), ("cram", 1), ("vsram", 2), ("vdpreg", 3), ("wram", 4)):
            (folder / f"{name}.bin").write_bytes(bytes(self.mem(which)))
        wh = self.lib.ps_frame_size()
        (folder / "frame.raw").write_bytes(bytes(self.mem(6)))
        (folder / "frame.txt").write_text(f"{wh >> 16} {wh & 0xFFFF}\n")

    # ---- rastreio (bit 0 = lido como dado, bit 1 = executado)
    def trace(self, on=True, clear=True):
        """Liga (limpando as marcas, se clear) ou desliga o rastreio; desligar preserva as marcas."""
        if on and clear:
            self.lib.ps_trace_clear()
        self.lib.ps_trace(1 if on else 0)

    def marks(self):
        return bytes(self.lib.ps_trace_marks().contents)

    def executed(self, addr):
        """Se o endereço foi executado desde o último trace(True)."""
        return bool(self.lib.ps_mark(addr) & 2)

    def watch(self, lo, hi):
        """Registra quem grava em [lo, hi) enquanto o rastreio estiver ligado."""
        self.lib.ps_watch(lo, hi)

    def watch_log(self):
        n = self.lib.ps_watch_len()
        p = ctypes.cast(self.lib.ps_watch_log(), ctypes.POINTER(ctypes.c_uint * (n * 3)))
        v = list(p.contents) if n else []
        return [(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)]

    def patch_rom(self, addr, data):
        """Altera a ROM carregada na memória do emulador (não toca no arquivo)."""
        rom = ctypes.cast(self.lib.ps_rom(), ctypes.POINTER(ctypes.c_ubyte * 0x400000)).contents
        for i, b in enumerate(data):
            rom[(addr + i) ^ 1] = b

    # ---- som
    def log_start(self):
        self.lib.ps_log_start()

    def log_stop(self):
        self.lib.ps_log_stop()
        n = self.lib.ps_log_len()
        buf = self.lib.ps_log_buf()
        return [(buf[i].frame, buf[i].cycles, buf[i].kind, buf[i].addr, buf[i].data) for i in range(n)]

    def write_vgm(self, path, writes, loop_frame=None):
        """VGM 1.50: YM2612 (0x52/0x53), SN76489 (0x50), esperas em amostras de 44,1 kHz."""
        if not writes:
            return 0
        f0 = writes[0][0]
        body = bytearray()
        pos = 0
        loop_off = None
        for fr, cyc, kind, addr, data in writes:
            t = round(((fr - f0) + min(cyc, self.MCLK_PER_FRAME) / self.MCLK_PER_FRAME) * 735)
            if loop_frame is not None and loop_off is None and fr >= loop_frame:
                loop_off = len(body)
                loop_pos = pos
            while t > pos:
                step = min(t - pos, 65535)
                body += b"\x62" if step == 735 else b"\x61" + struct.pack("<H", step)
                pos += step
            body += bytes((0x52 + kind, addr, data)) if kind < 2 else bytes((0x50, data))
        body += b"\x66"
        hdr = bytearray(0x40)
        hdr[0:4] = b"Vgm "
        struct.pack_into("<I", hdr, 0x04, 0x40 + len(body) - 4)
        struct.pack_into("<I", hdr, 0x08, 0x150)
        struct.pack_into("<I", hdr, 0x0C, 3579545)            # SN76489
        struct.pack_into("<I", hdr, 0x18, pos)                # total de amostras
        struct.pack_into("<I", hdr, 0x24, 60)
        struct.pack_into("<H", hdr, 0x28, 0x0009)             # feedback SN76489 (Sega)
        hdr[0x2A] = 16                                        # registrador de deslocamento
        struct.pack_into("<I", hdr, 0x2C, 7670453)            # YM2612
        struct.pack_into("<I", hdr, 0x34, 0x0C)               # dados em 0x40
        if loop_off is not None:
            struct.pack_into("<I", hdr, 0x1C, 0x40 + loop_off - 0x1C)
            struct.pack_into("<I", hdr, 0x20, pos - loop_pos)
        Path(path).write_bytes(bytes(hdr) + bytes(body))
        return pos / 44100
