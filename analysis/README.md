# Análise da ROM: Phantasy Star IV (USA)

ROM: `ps4.bin`, cópia de `Phantasy Star IV (USA).md`, 3 MB, cabeçalho "PHANTASY STAR The end of the millennium", GM MK-1307. O checksum do cabeçalho (`05CB`) bate com o calculado.

Tudo o que sai da ROM (gráficos, sons, texto, mapas, tabelas, o projeto do Ghidra e a listagem) fica em pastas fora do git. O repositório guarda só as ferramentas e esta documentação.

## Ferramentas

| Caminho | Uso |
|---|---|
| `ghidra_project/PS4.gpr` | Projeto do Ghidra 12.1.4 analisado, com nomes. Abra com `ghidraRun.bat`. |
| `ghidra_scripts/` | `SetupMD` (mapa de memória e vetores), `CoverMD` (cobertura por chamadas e tabelas), `CleanMD` (remove código falso), `ImportExecMD` (cobertura real do emulador), `NameMD` (nomes e tipos), `ExportMD`/`ExportAllMD` (exportação), `ExportZ80`, `FindDecompMD`, `FindTextMD`, `CallArgsMD`, `DumpMD`, `DecompMD`. |
| `emu/` | Emulador no PC: Genesis Plus GX compilado como DLL (`build.py`, com o Zig do PyPI) mais o frontend `pcfront.c`, controlado por `ps4emu.py`. Roda a ~1.500 quadros/s, sem tela. |
| `tools/` | Descompressores, extratores e conversores em Python, descritos nas seções abaixo. |
| `export/` | `functions.csv`, `listing.asm` e `decomp_all.c` (listagem e pseudocódigo de todas as funções), `exec_marks.bin` (cobertura real), CSVs de apoio. |

Ambiente: `py -3 -m venv analysis\.venv` e `analysis\.venv\Scripts\python.exe -m pip install ziglang`. Depois, `analysis\.venv\Scripts\python.exe analysis\emu\build.py` gera `emu/gpgx_pc.dll`.

Para reconstruir o projeto do Ghidra do zero (o nome da ROM não pode ter espaços nem parênteses, porque o `.bat` do Ghidra quebra com eles):

```
analyzeHeadless.bat analysis\ghidra_project PS4 -import analysis\ps4.bin -overwrite -loader BinaryLoader -processor 68000:BE:32:default -scriptPath analysis\ghidra_scripts -preScript SetupMD.java analysis\gg_decoded.csv
analyzeHeadless.bat analysis\ghidra_project PS4 -process ps4.bin -noanalysis -scriptPath analysis\ghidra_scripts -postScript CoverMD.java -postScript CleanMD.java -postScript ImportExecMD.java analysis\export\exec_marks.bin analysis\export\read_only_code.csv -postScript NameMD.java -postScript ExportMD.java analysis\export analysis\gg_decoded.csv -postScript ExportAllMD.java analysis\export
```

## Emulador no PC (`emu/`)

`ps4emu.Emu` carrega a ROM e oferece:
- **Controle:** quadros com entrada de controle e estados salvos em memória.
- **Memória:** leitura e escrita da RAM, VRAM, CRAM e registradores do VDP, e patch na ROM carregada.
- **Rastreio:** registra o que o 68000 executou e o que leu como dado (bitmap de 4 MB), e quem gravou num endereço vigiado (PC, endereço, valor). Usa o `HOOK_CPU` do núcleo.
- **Som:** registra as escritas no YM2612 e no PSG e grava VGM 1.50.

Foi assim que se resolveram, sem o celular, os mapas, a música, as taxas dos samples, a tabela de níveis e a cobertura real do código. Os estados de partida (`title.state`, o menu de título parado; `preload.state`, um quadro antes de a abertura carregar a primeira cidade) são gerados pelos próprios scripts ao percorrer o início do jogo.

## Mapa de memória

| Faixa | Uso |
|---|---|
| `000000-0001FF` | Vetores do 68000 e cabeçalho Sega |
| `000200-~09FFFF` | Código (batalha em `0x2000`-`0x9FFF`; campo, mapas, lojas e baús em `0x41000`-`0x7xxxx`; driver de som em `0xD0000`) |
| `0E0000-0FFFFF` | Samples PCM do DAC |
| `100000-1DFFFF` | Mapas: tabela `0x100000`, registros, tilesets Kosinski, sprites e retratos Nemesis, layouts |
| `1DF5CA-1FFFFF` | Diálogo (43 blocos Kosinski e mensagens sem compressão) |
| `280000-2ACxxx` | Tabelas de dados: nomes, inimigos, formações, zonas, níveis, itens, técnicas |
| `FF0000-FFFFFF` | RAM. O jogo acessa por endereço curto com sinal (`FFFFxxxx`). |

## Rotinas e variáveis identificadas

| Endereço | Nome | O que faz |
|---|---|---|
| `0x300A` | `Battle_GiveRewards` | Conta os membros vivos, lê o XP total de `FF41CE` e divide (`divu.w D2,D1`). Corta pela metade se `FFF43C` estiver ligada. Soma o meseta de `FF41D0`, com limite de 9.999.999. |
| `0x2D960` | `Battle_EnemyDefeated` | Soma XP (`+0x60`) e meseta (`+0x62`) do inimigo derrotado. |
| `0x7F5E` | `Battle_LoadEnemy` | Copia o registro de 48 bytes de `0x2816BC` para o objeto de batalha. |
| `0x7DFE` | `Battle_PickFormation` | Formação fixa (`FFECFC` ≥ 0) ou sorteada pela zona do mapa. |
| `0x3152` | `Battle_RollItemDrop` | Sorteia o item deixado. |
| `0x9178` / `0x6112A` | `Battle_/Field_SpendTechniqueTP` | `sub.w` do custo da técnica (`0x2A9BE0 + id*8 + 1`). |
| `0x65352` / `0x659EE` | `Shop_BuyItem` / `Shop_ChargeMeseta` | Compra e desconto do preço. |
| `0x58B7A` / `0x66C6A` | `Field_OpenChest` / `Field_ChestMesetaReward` | Baú; meseta = `FFECC2` × 100. |
| `0x44414` / `0x44652` | `NewGame_Init` / inicialização dos personagens | Grupo inicial, meseta 500, atributos de `0x2A8ACA`. |
| `0x5AE98` | `Map_Load` | Carrega o mapa de `FFEC28` (ver Mapas). |
| `0x6A090` | `Text_Interpreter` | Desenha o texto e executa os controles. |
| `0x57624`… / `0x57666`… | teste / liga flag | Flags de evento (ver Eventos). |
| `0x41BEA` / `0x41A90` / `0x41752` / `0x41740` | Kosinski / Enigma / Nemesis / Nemesis→VDP | Descompressores. |
| `0xD0008` / `0xD0C1A` | driver de som / carga do Z80 | Ver Som. |

| RAM | Conteúdo |
|---|---|
| `FFF500 + id*0x80` | Personagem: `+0x08` nível (0 = LV 1), `+0x0A` XP (32 bits), `+0x52` técnicas (16 IDs), `+0x62` skills (8 IDs), `+0x6A` usos de skill (8 pares atual/máx), `+0x0E`/`+0x10` HP máx/atual, `+0x12`/`+0x14` TP, `+0x18`/`+0x1B`/`+0x1E`/`+0x21` Força/Mental/Agilidade/Destreza (cópias de batalha logo depois), `+0x24` ataque, `+0x28` defesa, `+0x16` status (`0x44` = fora de combate). Inimigos usam a mesma estrutura. |
| `FFF438` | Meseta (32 bits) |
| `FFF40A` | Grupo (até 6 IDs, `FF` = vazio) |
| `FFEC20` | Modo do jogo (tabela `0x424DE`) |
| `FFEC28` / `FFEC2A` | Mapa atual / anterior; `FFEC44`-`FFEC4A` posição de chegada; `FFC030`/`FFC034` posição em pixels |
| `FF500A` | Fila de comandos de som (música, efeitos, controle) |
| `FF3000` | Bloco de diálogo descomprimido da área |
| `FF6000` / `FFB000` / `FFA000` / `FFEC64` | Blocos do mapa / camada de baixo / camada de cima / dimensões |
| `FFF100`-`FFF17F` | 4 bancos de flags de evento |

Os códigos Game Genie funcionam assim: `RE2A-A6V4` troca o `divu` por `nop`, e cada um recebe o XP total; `2J2A-AFV4` troca por `mulu`, multiplicando pelo tamanho do grupo; os de TP pulam o `sub.w`; o `AKNT-NA9R` pula a cobrança na loja; os de baú trocam o `#100`.

## Dados de jogo (`tools/export_game_data.py` → `assets/data/`)

| Arquivo | Fonte | Conteúdo |
|---|---|---|
| `enemies.csv` | `0x2816BC`, 48 bytes por ID; nome na lista `0x280D07`, índice ID+8 | 266 entradas: HP, Força, Mental, Agilidade, Destreza, ataque, defesa, 14 bytes de resistências, 16 bytes de ações, XP, meseta. Os campos saíram do carregador `0x7F5E`, que copia cada byte para o mesmo offset da estrutura de personagem. |
| `formations.csv`, `formations_fixed.csv` | 4 listas Kosinski de 128 (`0x283E6C`…) e `0x284F7C` | Cabeçalho, N inimigos, máscaras, pares (ID, posição X). |
| `zones.csv` | `0x2836EC` (Kosinski) | 68 zonas, 32 formações sorteadas com repetição (o peso). |
| `zones_motavia.png` / `_grid.csv`, `zones_mapa2.*` | `0x28501C` (64×64) e `0x2853CC` (64×32) | Zona de encontro por célula de 64 px. |
| `levels.csv` | ponteiros em `0x5D73A`, 22 bytes por nível | 11 personagens: XP necessário, HP/TP máximos e atributos por nível. Achado rastreando a tela de status ("NX"); bate com os códigos de nível inicial. Os 2 bytes `aprende_*` são IDs aprendidos no nível (hipótese: coincidem com o primeiro uso de um novo slot de skill). `usos_skill` é o máximo de usos dos 8 slots, que vão para os pares atual/máx em `+0x6A`. |
| `items.csv` | `0x2A8E3A`, 22 bytes; nomes `0x2AAFB4` | Preço, tipo, máscaras de equipamento e bônus. |
| `shops.csv` | `0x681A6`-`0x6829D` | 48 estoques de loja com preço. |
| `flags.csv` | `tools/export_flags.py` | 171 flags: quem liga, quem testa no código e quais mensagens dependem delas. |

Nomes dos 11 personagens em `0x280CD0`, com outra base de letras (`39` = a): Chaz, Alys, Hahn, Rune, Gryz, Rika, Demi, Wren, Raja, Kyra, Seth.

A validação do alinhamento dos nomes veio de duas fontes:
- **Famílias de variantes:** o deslocamento 8 é o único que deixa as famílias coerentes (Shadow/Frost/Blood Saber, Snow/Red/Hungry Mole…).
- **Zonas iniciais:** as zonas do começo de Motavia caem em Monsterfly, Crawler, Locusta, Sand Newt e Scorpirus.

## Mapas (`emu/dump_maps.py` → `assets/maps/`)

- **Registro:** `0x100000 + ID*4` aponta para o registro de cada mapa. Confirmado pelo rastreio, que leu `0x10004C` ao carregar a cidade, mapa `0x13`. A tabela vai até o primeiro registro (`0x100684`): 417 IDs, dos quais 361 têm mapa e o resto vale `0x200` (vazio).
  - **Tilesets:** pares (bloco de 256 tiles na VRAM, ponteiro **Kosinski**), terminados por `FFFF`.
  - **Sprites:** pares (tile inicial, ponteiro **Nemesis**), terminados por `FFFF`.
  - **Resto do registro:** dimensões, o ponteiro das definições de bloco, a lista de NPCs, a paleta e os layouts.
- **Bloco:** 4×4 tiles (16 palavras de nametable, 32×32 px). Isso foi confirmado contra a VRAM real: 15/15 blocos do plano A e 76/105 do B. As diferenças são tiles animados.
- **Camadas:** de baixo em `FFB000` e de cima em `FFA000`, esta com a cor 0 transparente. Dimensões em `FFEC64`.
- **Como o dump funciona:** a abertura grava o mapa inicial com `move.w #0x13,(FFEC28)` em `0x73E32` e chama `Map_Load`. O script troca o imediato por cada ID, deixa o próprio jogo carregar e compõe o mapa inteiro com os tiles e a paleta que ele montou.
  - **Tiles:** a VRAM é lida a cerca de 80 quadros, antes de o diálogo da abertura sobrescrever tiles com a janela de texto.
  - **Paleta:** a CRAM é lida a cerca de 200 quadros, depois do esmaecimento. Antes disso ela ainda tem as cores da cena anterior.
- `maps.csv` lista o status de cada ID e as duplicatas.
- **Resultado:** 346 mapas distintos renderizados, 12 IDs repetindo outro mapa, 2 grandes demais (`001` e `063`, 128×128) e o `000` (Motavia), que não carrega por esse método.
- **Mapas grandes:** os maiores que 64×64 blocos (o mundo de neve, ID 1, tem 128×128) não cabem nos buffers de 4 KB e são carregados em partes conforme o jogador anda. Ficam marcados como "grande: carregado em partes" e não são renderizados.

## Sprites (`emu/dump_sprites.py` → `assets/sprites/`)

Os conjuntos de sprite de cada mapa vêm do próprio registro. As folhas saem em quadros de 2×4 tiles (16×32 px, em colunas, como na tabela de sprites do VDP), com a linha de paleta que o sprite usa na tela depois do carregamento. Saíram 116 conjuntos. Em 20 a paleta foi confirmada por um sprite visível (`paleta_confirmada`); nos outros foi usada a linha 3, a dos personagens.

## Compressão

Os três formatos padrão da Sega, reimplementados em [`tools/sega_codecs.py`](tools/sega_codecs.py).

| Rotina | Formato | Uso |
|---|---|---|
| `0x41BEA` | Kosinski | tilesets de mapa, blocos, layouts, diálogo, tabelas |
| `0x41A90` | Enigma | mapas de tiles de telas fixas |
| `0x41752` / `0x41740` | Nemesis | sprites, retratos, fontes |

A validação foi feita de três formas:
- **Encadeamento:** cada recurso termina onde começa o seguinte (por exemplo, `1CC47A` + 2.608 = `1CCEAA`).
- **VRAM:** o Nemesis bate byte a byte com a VRAM de cenas reais (fonte `2A303A` 87/87, sprite do Chaz `121600` 72/72).
- **RAM:** o Kosinski é idêntico aos buffers da RAM, no diálogo e nos mapas.

| Ferramenta | Saída |
|---|---|
| `tools/extract_compressed.py` | `assets/compressed/`: os 89 recursos chamados diretamente |
| `tools/scan_nemesis.py` + `tools/render_scan.py` [despejo] | `assets/nemesis_scan/`: 834 fluxos Nemesis da ROM inteira, coloridos quando aparecem na cena |
| `tools/render_vdp.py` | VRAM, planos, sprites e quadro de um despejo do app ou do emulador |

## Som

- **Driver 68000** (`0xD0008`, RAM em `FF5000`): estilo SMPS, com trilhas de 0x30 bytes a partir de `FF5040` (DAC, FM, PSG e efeitos). O comando entra por `FF500A`.
  - `0x81`-`0xB4`: músicas e vinhetas.
  - `0xB5`-`0xF5`: efeitos.
  - `0xF6`-`0xFF`: controle (parar, esmaecer…).
  - A classificação completa está em `assets/sound/sound_ids.csv` (`emu/probe_sounds.py`).
- **VGM** (`emu/record_music.py`): **54 faixas** (`ps4_XX.vgm`) e 66 efeitos (`sfx_XX.vgm`). São gravações das escritas reais no YM2612 e no PSG, incluindo a bateria pelo DAC, a partir do menu de título silencioso. As músicas têm 150 s, o bastante para dar o loop.
- **MIDI** (`tools/vgm2mid.py`): uma trilha por canal (6 FM, 3 PSG e DAC como percussão no canal 10). As notas vêm das frequências dos registradores; os timbres não são convertidos.
- **Driver Z80** (`0xD153E`, 0x522 bytes; ver `z80/`): só toca samples PCM pelo DAC.
  - A trilha de DAC do 68000 manda a "nota" para `A01F02`, e ela escolhe um dos **29 casos de taxa** da tabela de salto `Z80:0170`.
  - Os casos vão de 2.000 Hz (`0x81`) a 10.227 Hz (`0x9D`) e foram medidos no emulador (`assets/sound/dac_rate_cases.csv`, `emu/probe_dac_rates.py`).
  - O mesmo sample toca em taxas diferentes conforme a nota.
- **Samples** (`tools/extract_samples.py`): 17 samples em `0x0E0000`-`0x0FFFFF`, contíguos.
  - `tools/sample_rates_from_vgm.py` mede a taxa típica de cada um nas músicas (7,1 a 9,6 kHz) e reescreve os WAV com ela.
  - 8 samples (`84`, `87`, `89`, `8A`, `8B`, `8C`, `8F`, `90`) não aparecem em nenhuma música nem efeito gravado.

## Texto

- **Tabelas de nomes** sem compressão (`01`-`1A` = A-Z, `FE`/`FF` terminam): `tools/dump_name_tables.py`.
- **Diálogo** completo: `tools/scan_kosinski_text.py` → `tools/export_dialogue.py` → `assets/text/dialogue.txt`, com 1.768 mensagens em 43 blocos Kosinski mais 27 sem compressão e **nenhum byte desconhecido**. Validado byte a byte contra o buffer `FF3000`.
- **Codificação** ([`tools/text_codec.py`](tools/text_codec.py)): `00` espaço, `01`-`1A` A-Z, `1B`-`34` a-z, `40`-`49` 0-9, `35` `.`, `36` `'`, `37` `,`, `39` `:`, `3A` `!`, `3B` `?`, `3C` `-`.

| Controle | Argumentos | Efeito (lido no interpretador `0x6A090`) |
|---|---|---|
| `F2 sub` | conforme `sub` | sub-rotina da tabela `0x6A550`; ver abaixo |
| `F4 n` | 1 | retrato do falante |
| `F5` | 0 | espera / pergunta |
| `F6 a b` | 2 | o interpretador só pula os 2 bytes |
| `F9 n` | 1 | pausa de n quadros |
| `FA f n` | 2 | se a flag `f` (banco `FFF100`) estiver ligada, pula `n` mensagens |
| `FC` / `FD` | 0 | nova linha / nova página |
| `F7` / `FF` | 0 | fim |

Subcódigos de `F2`, lidos nas próprias rotinas:

| Sub | Efeito |
|---|---|
| `00 hhll` | abre o quadro ilustrado `hhll` (`0x6AF9C` descomprime o gráfico Nemesis numa janela) |
| `01` / `02` | fecha o último quadro / todos |
| `03 x`, `04 x` | toca o som x |
| `05` | nada |
| `06` | ação de roteiro (`FFECD2`) |
| `07` | pisca a paleta com o som `0xCB` |
| `08` / `09` | pausa / retoma a música (`FF5007`) |
| `0A` | tremor de tela com o som `0xDB` |
| `0B f` | liga a flag f |
| `0C` | escurece e clareia a tela |

## Eventos (`tools/export_flags.py`)

As flags ficam em quatro bancos de 256 bits (`FFF100`, `FFF120`, `FFF140`, `FFF160`), com o bit 7 primeiro.
- **Testar:** `0x57624`, `0x5762E` e `0x57638`.
- **Ligar:** `0x57666`, `0x57670`, `0x5767A` e `0x57684`.
- **Apagar:** de `0x576A8` em diante.

O diálogo escolhe a fala por cadeias de `FA` no início de cada mensagem, e o código liga as flags em pontos de roteiro como a abertura (`0x73E80`). O mapa resultante está em `flags.csv`. Ficaram 20 chamadas com a flag num registrador calculado, não resolvidas estaticamente.

## Cobertura do código

| Etapa | Resultado |
|---|---|
| Análise a partir dos vetores (`SetupMD`) | 698 funções |
| Chamadas, `jsr abs.l` soltos e tabelas de 6+ ponteiros (`CoverMD`) | 3.060 |
| Remoção de código impossível num 68000 puro: instruções e modos do 68020+ (`CleanMD`) | 486 instruções e 210 funções falsas removidas; 2.850 |
| Cobertura real no emulador: título, abertura, cidade e campo com entrada aleatória, e o carregamento de todos os mapas (`emu/coverage.py`, `ImportExecMD`) | 13.288 instruções executadas, 95% já dentro de funções; 227 endereços desmontados e 372 funções novas; **3.158 funções** |
| Correções de início de função | `Battle_GiveRewards` (`0x303A` → `0x300A`) e `Field_ChestMesetaReward` (`0x66C72` → `0x66C6A`) |

`export/read_only_code.csv` lista as 67 instruções que o Ghidra trata como código, mas o jogo só leu como dado (tabelas embutidas no meio do código).

## Limites conhecidos

- **Batalha:** o código de batalha não foi coberto pela execução real. A cobertura não provocou nenhum encontro, e o mapa-múndi carregado pela abertura fica sem encontros. As rotinas de batalha vêm da análise estática.
- **Paletas:** a dos inimigos e a de telas que não são de mapa (batalha, retratos fora de uma cena capturada) não estão associadas. Os fluxos Nemesis desses recursos continuam em tons de cinza.
- **Campos sem nome:**
  - nos inimigos: `campo_12`, `campo_14`, os 14 bytes de resistências e os 16 de ações;
  - nos níveis: o significado exato dos 2 IDs `aprende_*`;
  - nos itens: o significado exato das máscaras e dos dois bytes de bônus.
- **Música:** o formato SMPS das sequências não foi decodificado nota a nota. VGM e MIDI saem da execução do driver.
- **Samples:** 8 samples sem uso observado e, portanto, sem taxa medida.
- **Eventos:** as 20 chamadas de flag com o número em registrador.
- **Mapas-múndi grandes:** Motavia (`000`) e os dois de 128×128 (`001`, `063`) não foram renderizados, porque são carregados em partes.
- **Sprites:** 96 dos 116 conjuntos de sprite usam uma paleta suposta (linha 3).
