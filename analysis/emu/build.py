"""Compila o Genesis Plus GX + pcfront.c como DLL do Windows (gpgx_pc.dll) com o Zig do PyPI.

Uso: analysis\\.venv\\Scripts\\python.exe analysis\\emu\\build.py
psg.c é compilado com psg_write renomeado para psg_write_real, para o frontend registrar as escritas.
HOOK_CPU liga o rastreio de execução/leitura do núcleo (core/debug), usado por ps_trace().
Mudar defines exige apagar emu/obj para recompilar tudo.
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

here = Path(__file__).resolve().parent
g = here.parent.parent / "app" / "src" / "main" / "cpp" / "gpgx"
lc = g / "libretro" / "libretro-common"
obj = here / "obj"
obj.mkdir(exist_ok=True)

core_dirs = [g / "core" / d for d in ("", "z80", "m68k", "ntsc", "sound", "sound/minimp3", "input_hw",
                                      "cd_hw", "cart_hw", "cart_hw/svp", "debug")]
sources = [p for d in core_dirs for p in sorted(d.glob("*.c"))]
sources += [lc / p for p in (
    "streams/file_stream.c", "streams/file_stream_transforms.c", "compat/fopen_utf8.c",
    "compat/compat_snprintf.c", "compat/compat_strl.c", "compat/compat_strcasestr.c",
    "compat/compat_posix_string.c", "encodings/encoding_utf.c", "file/file_path.c", "file/retro_dirent.c",
    "lists/string_list.c", "lists/dir_list.c", "memmap/memalign.c", "string/stdstring.c",
    "vfs/vfs_implementation.c")]
sources += [g / "libretro" / "deps" / "zlib-1.2.11" / f for f in
            ("adler32.c", "crc32.c", "inffast.c", "inflate.c", "inftrees.c", "zutil.c")]
sources += [g / "libretro" / "libretro.c", here / "pcfront.c"]

defines = ["INLINE=static inline", "USE_16BPP_RENDERING", "LSB_FIRST", "BYTE_ORDER=LITTLE_ENDIAN", "__LIBRETRO__",
           "FRONTEND_SUPPORTS_RGB565", "ALIGN_LONG", "ALIGN_WORD", "M68K_OVERCLOCK_SHIFT=20",
           "Z80_OVERCLOCK_SHIFT=20", "HAVE_YM3438_CORE", "USE_LIBRETRO_VFS", "HAVE_OPLL_CORE",
           "USE_PER_SOUND_CHANNELS_CONFIG", "MAXROMSIZE=16777216", "HOOK_CPU"]
includes = core_dirs + [g / "libretro", lc / "include", g / "libretro" / "deps" / "zlib-1.2.11"]
zig = [sys.executable, "-m", "ziglang", "cc", "-target", "x86_64-windows-gnu"]
# -fcommon: cpuhook.h define (não só declara) cpu_hook em todo arquivo que o inclui.
flags = ["-O2", "-w", "-fno-sanitize=undefined", "-fcommon"] + [f"-D{d}" for d in defines] + [f"-I{i}" for i in includes]


def compile_one(src):
    out = obj / (str(src.relative_to(g.parent.parent.parent.parent.parent)).replace(os.sep, "_").replace(":", "") + ".o")
    if out.exists() and out.stat().st_mtime > src.stat().st_mtime:
        return out
    extra = ["-Dpsg_write=psg_write_real"] if src.name == "psg.c" else []
    r = subprocess.run(zig + flags + extra + ["-c", str(src), "-o", str(out)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"falha em {src}:\n{r.stderr}")
    return out


with ThreadPoolExecutor(max_workers=os.cpu_count()) as ex:
    objs = list(ex.map(compile_one, sources))
dll = here / (sys.argv[1] if len(sys.argv) > 1 else "gpgx_pc.dll")
r = subprocess.run(zig + ["-shared", "-o", str(dll)] + [str(o) for o in objs], capture_output=True, text=True)
if r.returncode:
    raise SystemExit(r.stderr)
print(f"ok: {dll} ({len(objs)} objetos)")
