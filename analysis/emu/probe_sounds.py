"""Classifica os IDs de som: a partir do menu de título parado, grava cada ID em FF500A (fila de
comandos do driver) e mede notas FM (key-on no registrador 0x28), escritas PSG e DAC (0x2A).
Saída: assets/sound/sound_ids.csv. Uso: probe_sounds.py <estado-do-titulo>"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ps4emu import Emu  # noqa: E402

SECONDS = 12
e = Emu()
base = Path(sys.argv[1]).read_bytes()


def measure(writes):
    keyon = [w for w in writes if w[2] == 0 and w[3] == 0x28 and w[4] & 0xF0]
    psg = [w for w in writes if w[2] == 2 and w[4] & 0x90 == 0x90 and w[4] & 0x0F != 0x0F]  # volume != mudo
    dac = [w for w in writes if w[2] == 0 and w[3] == 0x2A]
    last = max([w[0] for w in keyon + psg] or [0])
    return len(keyon), len(psg), len(dac), last


e.load_state(base)
e.log_start()
e.run(60 * SECONDS)
f0 = e.lib.ps_frame_no() - 60 * SECONDS
k, p, d, last = measure(e.log_stop())
baseline = (k, p, d)
print("sem comando:", baseline)

rows = []
for sid in range(0x80, 0x100):
    e.load_state(base)
    e.poke(0xFF500A, sid)
    start = e.lib.ps_frame_no()
    e.log_start()
    e.run(60 * SECONDS)
    k, p, d, last = measure(e.log_stop())
    dur = (last - start) / 60 if last else 0
    kind = ("música" if k > 40 and dur > SECONDS - 2 else "efeito" if k or p or d else "silêncio/comando")
    rows.append({"id": f"{sid:02X}", "notas_fm": k, "notas_psg": p, "escritas_dac": d,
                 "ultimo_som_s": f"{dur:.1f}", "tipo": kind})
    print(rows[-1])

out = Path(__file__).resolve().parent.parent / "assets" / "sound"
out.mkdir(parents=True, exist_ok=True)
with open(out / "sound_ids.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
