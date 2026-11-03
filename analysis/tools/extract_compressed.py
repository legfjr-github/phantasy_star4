"""Descomprime os recursos referenciados diretamente pelas chamadas aos descompressores.

Lê export/decomp_calls.csv (gerado por CallArgsMD.java) e grava em assets/compressed/:
<formato>_<endereço>.bin e, para tiles, um PNG em tons de cinza (ou com a paleta de um despejo,
se passado: extract_compressed.py <pasta-do-despejo> [linha-da-paleta]).
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pngutil import GRAY, cram_palette, tiles_png  # noqa: E402
from sega_codecs import enigma, kosinski, nemesis  # noqa: E402

here = Path(__file__).resolve().parent.parent
rom = (here / "ps4.bin").read_bytes()
out = here / "assets" / "compressed"
out.mkdir(parents=True, exist_ok=True)
CODECS = {"00041bea": ("kosinski", kosinski), "00041a90": ("enigma", enigma),
          "00041752": ("nemesis", nemesis), "00041740": ("nemesis", nemesis)}

palette = GRAY
if len(sys.argv) > 1:
    palette = cram_palette((Path(sys.argv[1]) / "cram.bin").read_bytes(), int(sys.argv[2]) if len(sys.argv) > 2 else 0)


targets = {}
with open(here / "export" / "decomp_calls.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        a0 = r["a0"]
        if len(a0) == 6 and all(c in "0123456789ABCDEF" for c in a0) and 0x80000 <= int(a0, 16) < len(rom):
            targets.setdefault((CODECS[r["callee"]][0], int(a0, 16)), []).append(r["call_site"])

report = []
for (fmt, addr), sites in sorted(targets.items(), key=lambda kv: kv[0][1]):
    codec = {"kosinski": kosinski, "enigma": enigma, "nemesis": nemesis}[fmt]
    try:
        data, used = codec(rom, addr)
        name = f"{fmt}_{addr:06X}"
        (out / f"{name}.bin").write_bytes(data)
        if fmt != "enigma" and len(data) >= 32:
            tiles_png(out / f"{name}.png", data, palette)
        report.append({"format": fmt, "rom": f"{addr:06X}", "packed": used, "unpacked": len(data),
                       "ratio": f"{len(data) / used:.2f}" if used else "", "calls": " ".join(sites), "error": ""})
    except Exception as e:  # dados inválidos para o formato: registra e segue
        report.append({"format": fmt, "rom": f"{addr:06X}", "packed": "", "unpacked": "", "ratio": "",
                       "calls": " ".join(sites), "error": str(e)[:80]})

with open(out / "index.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=report[0].keys())
    w.writeheader()
    w.writerows(report)
ok = [r for r in report if not r["error"]]
print(f"{len(ok)}/{len(report)} recursos descomprimidos")
for r in report:
    print(r["format"], r["rom"], r["packed"], "->", r["unpacked"], r["error"])
