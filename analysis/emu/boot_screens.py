"""Telas de abertura: liga o jogo sem apertar nada e grava cada tela diferente (logo da SEGA, a
apresentação que roda sozinha e o título), um quadro a cada 10, até 7.000 quadros (~2 min, uma volta da apresentação).
Quadros quase iguais (menos de 5% dos pixels diferentes do último salvo) são pulados.
Saída: assets/screens/boot_<quadro>.png.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from ps4emu import Emu  # noqa: E402

root = Path(__file__).resolve().parent.parent
out = root / "assets" / "screens"
out.mkdir(parents=True, exist_ok=True)
e = Emu()
last, saved = None, 0
for frame in range(10, 7010, 10):
    e.run(10)
    raw = bytes(e.mem(6))
    if not any(raw):
        continue
    if last is not None:
        diff = sum(1 for i in range(0, len(raw), 64) if raw[i:i + 2] != last[i:i + 2])
        if diff < len(raw) // 64 * 0.05:
            continue
    last = raw
    e.screenshot(out / f"boot_{frame:05d}.png")
    saved += 1
print(saved, "telas")
