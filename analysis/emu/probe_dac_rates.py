"""Mede a taxa de reprodução de cada caso da tabela de salto do driver Z80 (Z80:0170).

Caixa de comandos na RAM do Z80: 1F00 = sample (0x81..), 1F02 = caso de taxa (0x81..), 1F01 = disparo.
Para cada caso, toca o sample 0x81 a partir do estado do título e mede o intervalo entre escritas no
registrador 0x2A. Grava assets/sound/dac_rate_cases.csv. Uso: probe_dac_rates.py <estado-do-titulo>
"""
import csv
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ps4emu import Emu  # noqa: E402

MCLK = 53693175
e = Emu()
base = Path(sys.argv[1]).read_bytes()
rows = []
for case in range(0x81, 0xA0):
    e.load_state(base)
    z = e.mem(5)
    z[0x1F02] = case
    z[0x1F00] = 0x81
    z[0x1F01] = 0x01
    e.log_start()
    e.run(30)
    dac = [fr * Emu.MCLK_PER_FRAME + cyc for fr, cyc, k, a, d in e.log_stop() if k == 0 and a == 0x2A]
    gaps = [b - a for a, b in zip(dac, dac[1:]) if 0 < b - a < 40000]
    rate = round(MCLK / statistics.median(gaps)) if len(gaps) > 50 else None
    rows.append({"caso": f"{case:02X}", "escritas": len(dac), "taxa_hz": rate or ""})
    print(rows[-1])
out = Path(__file__).resolve().parent.parent / "assets" / "sound" / "dac_rate_cases.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
