"""Mapas-múndi grandes (128x128 blocos), que o jogo lê da ROM em pedaços enquanto o jogador anda.

Formato (mapa 1, confirmado pelo rastreio do carregamento): depois dos dados Kosinski dos blocos vêm
duas tabelas de 16 ponteiros, uma por camada (baixo e cima). Cada ponteiro aponta para um pedaço de
1024 bytes sem compressão = 8 linhas de 128 blocos; os 16 empilhados formam o mapa. Faixas iguais
são compartilhadas (vários ponteiros para o mesmo pedaço).
Os blocos (4x4 tiles) ficam em FF6000 e os tiles na VRAM, como nos outros mapas.
Uso: dump_bigmaps.py <estado-antes-do-carregamento> [IDs hex, padrão 0,1]
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from ps4emu import Emu, C  # noqa: E402
from maplib import compose  # noqa: E402
from pngutil import png  # noqa: E402
from sega_codecs import kosinski  # noqa: E402

root = Path(__file__).resolve().parent.parent
rom = (root / "ps4.bin").read_bytes()
out = root / "assets" / "maps"
base = Path(sys.argv[1]).read_bytes()
ids = [int(x, 16) for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else ["0", "1"])]


def chunk_tables(lo, hi):
    """Posições de tabelas de 16 ponteiros para pedaços de 1024 bytes logo depois da própria tabela."""
    found = []
    for t in range(lo + (lo & 1), hi, 2):  # ponteiros ficam em endereço par
        ptrs = struct.unpack_from(">16I", rom, t)
        data = t + 64
        if all(data <= p < data + 16 * 1024 and (p - data) % 1024 == 0 for p in ptrs):
            found.append((t, ptrs))
    return found


e = Emu()
title = Path(sys.argv[1]).with_name("title.state")
for mid in ids:
    if mid == 0:
        # Motavia já é o mapa corrente no estado de partida (a abertura passa por ele antes da cidade),
        # então trocar o imediato não recarrega nada. Captura o carregamento real da abertura:
        # move.w #0,(FFEC28) em 0x73B92 e retorno de Map_Load em 0x73BC2.
        from ps4emu import START  # noqa: E402
        e.load_state(title.read_bytes())
        e.press(START)
        e.run(180)
        e.trace(True)
        for _ in range(700):
            e.press(C, 3, 20)
            if e.executed(0x73BC2):
                break
    else:
        e.load_state(base)
        e.patch_rom(0x73E34, mid.to_bytes(2, "big"))
        e.press(C, 3, 20)
        e.trace(True)
        for _ in range(600):
            e.run(1)
            if e.executed(0x73E62):
                break
    marks = e.marks()
    e.trace(False)
    ram, vram = e.ram(), e.vram()
    if e.peek(0xFFEC28, 2) != mid:
        print(f"mapa {mid:#x}: não carregou por este método")
        continue
    # As duas tabelas vêm logo depois dos dados Kosinski dos blocos. No registro, o ponteiro dos blocos
    # vem depois das dimensões repetidas (7F7F 7F7F = 128x128) e de 0100 0001 0001.
    record = struct.unpack_from(">I", rom, 0x100000 + mid * 4)[0]
    at = rom.find(b"\x01\x00\x00\x01\x00\x01", record, record + 0x400)
    blocks_ptr = struct.unpack_from(">I", rom, at + 6)[0]
    _, used = kosinski(rom, blocks_ptr)
    tables = chunk_tables(blocks_ptr + used, blocks_ptr + used + 0x9000)
    if not tables:
        print(f"mapa {mid:#x}: tabelas de pedaços não encontradas")
        continue
    e.run(300)  # a abertura esmaece por mais tempo que um carregamento comum
    c = bytes(e.mem(1))
    pal = []
    for i in range(64):
        v = struct.unpack_from("<H", c, i * 2)[0]
        pal.append(((v >> 6 & 7) << 9) | ((v >> 3 & 7) << 5) | ((v & 7) << 1))
    # Cada pedaço é uma faixa de 8 linhas inteiras (128 blocos); os 16 empilhados formam o mapa.
    # (Medido: só essa leitura tem coerência espacial nas duas direções.)
    layers = [b"".join(rom[p:p + 1024] for p in ptrs) for t, ptrs in tables[:2]]
    # A ordem das duas tabelas muda de mapa para mapa (em Dezolis a primeira é o plano A, da frente).
    # Decide pelo buffer de baixo (FFB000): a tabela cujo conteúdo contém a janela carregada ali é a
    # camada de baixo; a outra vai por cima, com a cor 0 transparente.
    probe = ram[0xB000:0xB000 + 16]
    if probe not in layers[0] and probe in layers[1]:
        layers.reverse()
    # Em Dezolis as faixas 8-15 apontam todas para a faixa 7 (enchimento): o mapa útil tem 64 linhas.
    strips = 16
    while strips > 1 and all(ptrs[strips - 1] == ptrs[strips - 2] for _, ptrs in tables[:2]):
        strips -= 1
    W, H, img = compose(vram, pal, ram[0x6000:0xA000], layers, 128, strips * 8, 128)
    png(out / f"map_{mid:03X}.png", W, H, img)
    print(f"mapa {mid:#x}: tabelas em {[f'{t:06X}' for t, _ in tables[:2]]} -> map_{mid:03X}.png")
