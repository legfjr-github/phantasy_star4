"""Grava as músicas e vinhetas em VGM e mede a taxa real dos samples do DAC.

Para cada ID classificado como música/vinheta em sound_ids.csv: carrega o estado do menu de título
(silencioso), grava o ID em FF500A e registra as escritas no YM2612/PSG. Músicas: 150 s; o
restante para após 3 s de silêncio. Taxa do DAC: casa cada trecho contínuo de escritas no
registrador 0x2A com os samples de assets/sound e mede o intervalo médio entre bytes.
Uso: record_music.py <estado-do-titulo>
"""
import csv
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ps4emu import Emu  # noqa: E402

root = Path(__file__).resolve().parent.parent
snd = root / "assets" / "sound"
vgm_dir = snd / "vgm"
vgm_dir.mkdir(parents=True, exist_ok=True)
base = Path(sys.argv[1]).read_bytes()
effects = "--efeitos" in sys.argv  # grava também os efeitos sonoros (0xB5 em diante) como sfx_XX.vgm
ids = [r for r in csv.DictReader(open(snd / "sound_ids.csv", encoding="utf-8"))
       if (r["tipo"] == "música" or (r["tipo"] == "efeito" and int(r["id"], 16) < 0xB5)) != effects
       and r["tipo"] != "silêncio/comando"]

e = Emu()
samples = {p.stem: p.read_bytes()[44:] for p in snd.glob("sample_*.wav")}
dac_gaps = {}
summary = []
for r in ids:
    sid = int(r["id"], 16)
    looping = r["tipo"] == "música"
    e.load_state(base)
    e.poke(0xFF500A, sid)
    e.log_start()
    limit = 150 * 60 if looping else 60 * 60
    silent = 0
    for _ in range(limit // 30):
        before = e.lib.ps_log_len()
        e.run(30)
        sounding = e.lib.ps_log_len() - before > 4
        silent = 0 if sounding else silent + 30
        if not looping and silent >= 180:
            break
    writes = e.log_stop()
    secs = e.write_vgm(vgm_dir / f"{'sfx' if effects else 'ps4'}_{sid:02X}.vgm", writes)

    # Trechos de DAC: escritas em 0x2A com intervalo < 2000 mclk entre si.
    dac = [(fr * Emu.MCLK_PER_FRAME + cyc, d) for fr, cyc, k, a, d in writes if k == 0 and a == 0x2A]
    run = [dac[0]] if dac else []
    for prev, cur in zip(dac, dac[1:]):
        if cur[0] - prev[0] < 2000:
            run.append(cur)
            continue
        if len(run) > 200:
            data = bytes(x[1] for x in run)
            for name, pcm in samples.items():
                if data[20:84] and data[20:84] in pcm:
                    gaps = [b[0] - a[0] for a, b in zip(run, run[1:])]
                    dac_gaps.setdefault(name, []).append(statistics.median(gaps))
                    break
        run = [cur]
    summary.append({"id": f"{sid:02X}", "tipo": r["tipo"], "segundos": f"{secs:.1f}", "escritas": len(writes)})
    print(summary[-1])

with open(snd / ("sfx_index.csv" if effects else "vgm_index.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=summary[0].keys())
    w.writeheader()
    w.writerows(summary)

MCLK = 53693175  # NTSC
with open(snd / "sample_rates.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["sample", "intervalo_mclk", "taxa_hz", "trechos_medidos"])
    for name in sorted(samples):
        if name in dac_gaps:
            g = statistics.median(dac_gaps[name])
            w.writerow([name, f"{g:.0f}", f"{MCLK / g:.0f}", len(dac_gaps[name])])
        else:
            w.writerow([name, "", "", 0])
print("taxas:", {k: round(MCLK / statistics.median(v)) for k, v in dac_gaps.items()})
