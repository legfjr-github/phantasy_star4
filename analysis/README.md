# Análise da ROM: Phantasy Star IV (USA)

ROM: `ps4.bin`, cópia de `Phantasy Star IV (USA).md`, 3 MB, cabeçalho "PHANTASY STAR The end of the millennium", GM MK-1307. O checksum do cabeçalho (`05CB`) bate com o calculado.

## Arquivos

| Caminho | Conteúdo |
|---|---|
| `ghidra_project/PS4.gpr` | Projeto do Ghidra 12.1.4, já analisado e com nomes. Abra com `ghidraRun.bat`. |
| `ghidra_scripts/SetupMD.java` | Monta o mapa de memória do Mega Drive (ROM, Z80, I/O, VDP, RAM) e cria funções a partir dos 64 vetores do 68000. |
| `ghidra_scripts/NameMD.java` | Aplica os nomes e tipos listados abaixo, inclusive o espelho da RAM em `0xFFFF0000`. |
| `ghidra_scripts/ExportMD.java` | Exporta a lista de funções e o pseudocódigo das rotinas tocadas pelos códigos Game Genie. |
| `gg_decoded.csv` | Os 92 patches Game Genie do app convertidos em endereço, palavra original e palavra nova. |
| `export/functions.csv` | 2.850 funções: endereço, nome, tamanho, chamadores e chamadas. |
| `export/decomp_candidates.csv`, `export/decomp_calls.csv` | Ranking de descompressores e chamadas com o ponteiro de origem. |
| `export/gg_functions.c` | Pseudocódigo das 9 funções que contêm patches de código. |
| `export/gg_loose.asm` | Patches que caíram fora de uma função reconhecida. |

Para reconstruir do zero (o nome da ROM sem espaços nem parênteses é obrigatório, porque o `.bat` do Ghidra quebra com eles):

```
analyzeHeadless.bat analysis\ghidra_project PS4 -import analysis\ps4.bin -overwrite -loader BinaryLoader -processor 68000:BE:32:default -scriptPath analysis\ghidra_scripts -preScript SetupMD.java -postScript NameMD.java -postScript ExportMD.java analysis\export analysis\gg_decoded.csv
```

## Mapa de memória

| Faixa | Uso |
|---|---|
| `000000-0001FF` | Vetores do 68000 e cabeçalho Sega |
| `000200-~1FFFFF` | Código (batalha em `0x3000` e `0x9000`; campo, lojas e baús em `0x41000` a `0x6Bxxx`; rotinas auxiliares em `0x27Dxxx`) |
| `2A8000-2A9FFF` | Tabelas de dados: personagens iniciais, itens, técnicas e skills |
| `FF0000-FFFFFF` | RAM de 64 KB. O jogo acessa por endereço curto com sinal, que aparece como `FFFFxxxx`. |

## O que foi identificado

Observado no pseudocódigo e nos bytes da ROM:

| Endereço | Nome | O que faz |
|---|---|---|
| `0x303A` | `Battle_GiveRewards` | `divu.w D2,D1` divide o XP total pelo número de membros vivos e soma em `Character.xp`, com limite de 9.999.999. Logo antes, `tst.w $F43C / lsr.w #1,D1` corta o XP pela metade quando a flag `FFF43C` está ligada. No fim, soma `Battle_MesetaReward` ao `Party_Meseta`. |
| `0x3152` | `Battle_RollItemDrop` | Sorteia o item deixado pelo inimigo. |
| `0x9178` | `Battle_SpendTechniqueTP` | `sub.w` do custo da técnica (`Table_Techniques + id*8 + 1`) no TP do personagem. |
| `0x6112A` | `Field_SpendTechniqueTP` | Mesma coisa, fora de batalha. |
| `0x65352` / `0x659EE` | `Shop_BuyItem` / `Shop_ChargeMeseta` | Compara o preço com o meseta e desconta. |
| `0x58B7A` | `Field_OpenChest` | Abertura de baú. |
| `0x44414` | `NewGame_Init` | Zera o estado, copia os personagens de `2A8DA0`, define o grupo inicial (Chaz e Alys) e meseta = 500. |
| `0x41682` | `WaitVBlank` | Espera um quadro. É chamada em quase todo laço de menu. |

| RAM | Nome | Tipo |
|---|---|---|
| `FFF438` | `Party_Meseta` | 32 bits, limite de 9.999.999 |
| `FFF40A` | `Party_Members` | até 6 IDs, `0xFF` = vazio |
| `FFF500 + id*0x80` | `Characters[11]` | `+0x0A` xp (32 bits), `+0x12` tp, `+0x16` status (`0x44` = fora de combate), `+0x7A` flag de level-up |
| `FF41D0` | `Battle_MesetaReward` | meseta da batalha atual |
| `FFEF03` | `Pad1_Pressed` | botões apertados (`0x70` = A/B/C) |

Como os códigos funcionam (palavra original → nova):

- `RE2A-A6V4`: `divu.w D2,D1` → `nop`. Cada membro recebe o XP total, sem dividir.
- `2J2A-AFV4`: `divu.w` → `mulu.w D2,D1`. O XP é multiplicado pelo número de membros.
- `AJJT-NA4G` / `ALJT-AA6N`: `sub.w D0,(d,A0)` → `bra.s +2`. O TP nunca é descontado.
- `AKNT-NA9R`: pula a subtração em `Shop_ChargeMeseta`.
- O código antigo `FFF43A:00FF` grava só a palavra baixa de `Party_Meseta`. Por isso não dava "meseta infinito".

## Cobertura e limpeza do código

| Etapa | Script | Resultado |
|---|---|---|
| Análise automática a partir dos vetores | `SetupMD.java` | 698 funções |
| Alvos de `jsr`/`jmp`/`bsr`, padrões soltos de `jsr abs.l` e tabelas de 6+ ponteiros para código (rótulos `PtrTable_xxxxxx`) | `CoverMD.java` | 3.060 funções |
| Remoção de código falso: instruções e modos de endereçamento que só existem do 68010/68020 em diante (`rtm`, `moves`, índice com escala, `[...]`, `mulu.l`…), impossíveis num 68000 | `CleanMD.java` | 486 instruções inválidas, 210 funções falsas removidas, 57 trechos limpos (marcador "Cleanup"). Restam **2.850 funções**. |

Ordem para reconstruir: `SetupMD` (pre) → análise → `CoverMD` → `CleanMD` → `NameMD` → `ExportMD`.

## Compressão

O jogo usa os três formatos padrão da Sega. Identifiquei as rotinas ([`FindDecompMD.java`](ghidra_scripts/FindDecompMD.java) pontua candidatas por operações de bit, leitura `(An)+` e chamadores com ponteiro da ROM) e reimplementei em [`tools/sega_codecs.py`](tools/sega_codecs.py).

| Rotina | Formato | Uso |
|---|---|---|
| `0x41BEA` `KosinskiDec` | Kosinski (LZ com campo de descrição de 16 bits) | dados gerais e tiles |
| `0x41A90` `EnigmaDec` | Enigma | mapas de tiles (planos) |
| `0x41752` `NemesisDec` / `0x41740` `NemesisDecToVDP` | Nemesis (Huffman de nibbles, modo XOR) | a maior parte dos gráficos |

Validação:
- **Encadeamento:** os tamanhos consumidos encadeiam os recursos. Por exemplo, `1CC47A` + 2.608 = `1CCEAA`, onde começa o seguinte.
- **Comparação com a VRAM:** o Nemesis bate byte a byte com a VRAM de uma cena real. `27D778` dá 28/28 tiles, `2A303A` (fonte) 87/87 e `121600` (sprite do Chaz) 72/72.

| Ferramenta | Saída |
|---|---|
| `tools/extract_compressed.py` | `assets/compressed/`: os 89 recursos chamados diretamente (`lea abs,A0` antes da chamada), em `.bin` e `.png`, com `index.csv` |
| `tools/scan_nemesis.py` [despejo] | `assets/nemesis_scan/`: varredura da ROM inteira, 834 fluxos Nemesis e 71.851 tiles, incluindo os carregados por tabela de ponteiros; `vram_hits` no `index.csv` |
| `tools/render_scan.py` [despejo] | PNG de cada fluxo; 31 saem com as cores da cena |

Os PNG sem cena associada saem em tons de cinza, porque as paletas são carregadas à parte. Os tiles de sprite ficam em colunas e por isso aparecem "fatiados" numa folha de 16 colunas.

## Gráficos de uma cena (via emulador)

No app, menu ≡ → "Exportar gráficos (análise)" grava `vram.bin`, `cram.bin`, `vsram.bin`, `vdpreg.bin`, `wram.bin` e o quadro em `Android/data/br.emu.ps4/files/dumps/<hora>/`. Depois:

```
adb pull /sdcard/Android/data/br.emu.ps4/files/dumps analysis/dumps
py -3 analysis/tools/render_vdp.py <pasta-do-despejo> <saída>
```

O resultado traz as paletas, os 2.048 tiles da VRAM nas 4 paletas, os planos A e B, os sprites e o quadro. Exemplo em `assets/graphics/scene1/`. Atenção: o núcleo guarda VRAM e RAM com as palavras em little-endian, e o script já corrige isso.

## Som

- `0xD0C1A` `Sound_LoadZ80Driver` copia 0x522 bytes de `0xD153E` para a RAM do Z80. O blob está em `z80/z80_driver.bin`, com projeto Ghidra Z80, listagem `z80/z80_driver.asm` e pseudocódigo `z80/z80_driver.c` ([`ExportZ80.java`](ghidra_scripts/ExportZ80.java)).
- O Z80 é **só um tocador de samples PCM pelo DAC**.
  - **Caixa de comandos:** `1F00` e `1F01`, com o sample em `1F02` menos `0x81` e o pan em `1F04`.
  - **Registradores do YM2612:** `0x2B` liga o DAC e `0x2A` recebe o dado.
  - **Seleção de samples:** a tabela `Z80:0500` guarda (banco, índice). O banco N aponta para `0x0E0000 + N*0x8000` na ROM, e cada banco começa com cabeçalhos de 8 bytes: início, tamanho, início do loop e tamanho do loop.
- `tools/extract_samples.py` gera `assets/sound/sample_81.wav` a `sample_91.wav`, 17 samples de 8 bits. Os blocos são contíguos na ROM, o que confirma o formato. A taxa usada (11.025 Hz) é aproximada: a real depende do atraso de cada caso na tabela de salto do driver (`Z80:0170`).
- A música FM é sequenciada pelo 68000, com RAM de trabalho em `FF5000` e código perto de `0xD0000`. O formato da sequência ainda não foi documentado.

## Texto

- **Tabelas de nomes**, sem compressão: `0x01`–`0x1A` = A–Z, `0x31` entre palavras e `FE`/`FF` como terminadores. `tools/dump_name_tables.py` → `assets/text/name_tables.txt`, com 41 listas: classes, monstros (`280D08`…), itens (`2AAFB4`, 200 nomes), técnicas e lugares.
- **Diálogo: decodificado por completo.** `tools/scan_kosinski_text.py` → `tools/export_dialogue.py` → [`assets/text/dialogue.txt`](assets/text/dialogue.txt), com 1.768 mensagens em 43 blocos e mais 27 sem compressão, cerca de 249 mil caracteres e **nenhum byte desconhecido**.
  - **Armazenamento:** 43 blocos **Kosinski** contíguos em `1DF5CA`–`1FE650`, um por área do jogo. O jogo descomprime o bloco da área atual para a RAM em `FF3000` (`Dialogue_Buffer`). No fim da faixa, em `1FE650`, ficam as mensagens de "examinar" sem compressão.
  - **Interpretador:** `0x6A090` `Text_Interpreter`.
  - **Codificação** ([`tools/text_codec.py`](tools/text_codec.py)):
    - `00` espaço, `01`–`1A` A–Z, `1B`–`34` a–z, `40`–`49` 0–9
    - `35` `.`, `36` `'`, `37` `,`, `39` `:`, `3A` `!`, `3B` `?`, `3C` `-`

  | Controle | Argumentos | Uso |
  |---|---|---|
  | `F2 sub` | `sub 00`: 2 bytes; `03`/`04`: 1; demais: 0 | sub-rotina da tabela `0x6A550` (eventos, nomes) |
  | `F4 n` | 1 | retrato do falante |
  | `F5` | 0 | pergunta / espera |
  | `F6 a b` | 2 | — |
  | `F9 n` | 1 | pausa de n quadros |
  | `FA a b` | 2 | condição (início de bloco de falas alternativas) |
  | `FC` / `FD` | 0 | nova linha / nova página |
  | `F7` / `FF` | 0 | fim da mensagem |

  - **Validação:**
    - **Bytes:** o bloco `1E2680` descomprimido é idêntico byte a byte (5.388/5.388) ao buffer da RAM capturado com "This is the village of Krup." na tela.
    - **Ponteiro:** o ponteiro em `FF4FD4` aponta para o fim da mensagem exibida.
  - **Por que a busca anterior falhou:** as tabelas de nomes usam outra base (`01` = A, sem minúsculas), e no diálogo os literais do Kosinski ficam intercalados com campos de descrição de 16 bits. Por isso só apareciam pedaços de palavras.
  - **Tamanhos inferidos por estatística:** os argumentos de `F2 00` (2 bytes) e de `F6` saíram de estatística sobre os blocos, sem leitura das sub-rotinas da tabela `0x6A550`, e o significado de `F6` e dos subcódigos de `F2` ainda não foi documentado.

## Limites conhecidos

- **Funções:** as 2.850 incluem algumas criadas por heurística (tabelas de ponteiros). Pode haver falsos positivos que não usam instruções exclusivas do 68020.
- **Código fora das tabelas de salto:** o código chamado só via `jmp (d,PC,Dn)` com tabela de deslocamentos de 16 bits ainda pode faltar.
- **Rotina mal delimitada:** `Field_ChestMesetaReward` (`0x66C72`) continua errada, porque o patch cai no valor imediato `#100` de uma instrução.
- **Patches sem pseudocódigo:** os de `2A8xxx` a `2A9xxx` são dados de tabela.
- **Pendentes:** o formato da música FM, as paletas de cada recurso estático e o significado dos subcódigos de `F2` e de `F6` no texto.
