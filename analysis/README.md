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

Foi assim que se resolveram, sem o celular, os mapas, as batalhas, a música, as taxas dos samples, a tabela de níveis e a cobertura real do código. Os estados de partida (`title.state`, o menu de título parado; `preload.state`, um quadro antes de a abertura carregar a primeira cidade) são gerados pelos próprios scripts ao percorrer o início do jogo.

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
| `enemies.csv` | `0x2816BC`, 48 bytes por ID; nome na lista `0x280D07`, índice ID+8 | 266 entradas: HP, Força, Mental, Agilidade, Destreza, ataque, defesa, 14 bytes de resistências, IA, XP, meseta. Os campos saíram do carregador `0x7F5E`, que copia cada byte para o mesmo offset da estrutura de personagem. A IA (`0xCFE6`) lê `gatilhos_ia` (4 bytes em `+0x50`; cada um diferente de 0 chama uma rotina que pode forçar a ação) e `acoes_sorteadas` (8 ações em `+0x58`, sorteadas por `rand & 7` sem repetir a anterior). `ia_extra` (`+0x54`) não é lido por ela. |
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
  - **Momento da leitura:** o script espera o retorno de `Map_Load` (`0x73E62`, pelo rastreio de execução), copia RAM e VRAM nesse instante e lê a CRAM 120 quadros depois, quando o esmaecimento terminou. Assim o diálogo da abertura ainda não sobrescreveu tiles e a paleta já é a do mapa novo.
- A composição (blocos, camadas, transparência da camada de cima) fica em `emu/maplib.py`, usada pelos dois scripts.
- `maps.csv` lista o status de cada ID e as duplicatas.
- **Mapas-múndi** (`emu/dump_bigmaps.py`): Motavia (`000`) e Dezolis (`001`) têm 128×128 blocos e não cabem nos buffers de 4 KB. O jogo lê o layout direto da ROM conforme o jogador anda:
  - no registro, o ponteiro dos blocos vem depois do padrão `0100 0001 0001`;
  - logo depois dos dados Kosinski dos blocos ficam duas tabelas de 16 ponteiros, uma por camada;
  - cada ponteiro aponta para um pedaço de 1.024 bytes sem compressão, uma faixa de 8 linhas inteiras de 128 blocos. Os 16 empilhados formam o mapa, e faixas iguais são compartilhadas. A leitura em faixas foi escolhida por ser a única com coerência espacial nas duas direções.
  - O `000` já é o mapa corrente no estado de partida, então trocar o imediato não recarrega nada. O script captura o carregamento real da abertura (`move.w #0,(FFEC28)` em `0x73B92`, retorno em `0x73BC2`).
  - A ordem das duas tabelas muda: em Motavia a primeira é a camada de baixo; em Dezolis é a de cima (plano A, as montanhas). O script decide comparando com o buffer de baixo `FFB000`, conferido contra a nametable real da tela.
  - Em Dezolis as faixas 8-15 apontam todas para a faixa 7 (enchimento), então o mapa sai com 128×64 blocos.
- **Paleta de mapa:** ao carregar, o jogo monta a paleta-alvo em `FFFB00` (o esmaecimento parte dela). As linhas 0, 1 e 3 vêm dos 96 bytes de paleta do registro (por exemplo `0x119604` em Dezolis) e a linha 2 é a dos personagens (`0x296300`).
- **Resultado:** 351 mapas renderizados e 10 IDs repetindo outro mapa. O `063`, que parecia grande, tem 32×32 e sai pelo método normal.
- `emu/explore.py` anda ao acaso a partir de um estado e salva um estado na entrada de cada mapa novo, para uso dos outros scripts.

## Batalhas (`emu/battle_session.py` → `assets/battles/`)

As batalhas saem de encontros naturais. Forçar uma batalha pelo evento `0x9F` ou pela tela de nomes travou o jogo em `0x200`. O script entra em cada mapa com zona de encontro entre 2 e `0xFE` (tabela por mapa em `0x8050`), anda até a batalha começar e grava:
- `battles.csv`: mapa, zona, inimigos, gráficos lidos (endereço + tamanho), vitória e travamento;
- `battle_<mapa>_<n>.png` e `cram_*.bin`: a tela e a paleta de cada batalha;
- a cobertura de execução, somada a `export/exec_marks.bin`.

Foram 99 batalhas em 58 inimigos diferentes (`tools/battle_index.py` → `enemies_seen.csv` e `pal_*.png`, a paleta real de cada inimigo).

O carregador de gráficos de inimigo é `0x7C56`. Ele usa a tabela `0x27F3B8` (153 entradas de 20 bytes) e monta os quadros em `0x10FCE`.

### Todos os inimigos (`emu/enemy_gallery.py` → `assets/enemies/`)

Os encontros naturais só mostram o que o passeio aleatório alcança. A galeria força cada inimigo:
1. `emu/battlelib.py` acha um encontro numa masmorra e guarda o estado e o passo que levam a ele. O emulador é determinístico: repetir o passo repete o encontro.
2. Na ROM carregada, a leitura da formação passa a vir de um registro montado em espaço livre (`0x2F5000`): `lea (0x2F5000).l,A0` em `0x7F00` e `bra.b 0x7F14` em `0x7F06`. O registro é o de uma formação comum de 1 inimigo, com o ID trocado.
3. As 27 formações fixas (`0x284F7C`: chefes e batalhas de roteiro) entram com os próprios bytes.

Saem a tela (`enemy_<id>.png`, `fixed_<n>.png`), a CRAM e o inimigo recortado com fundo transparente (`enemy_<id>_spr.png`).

O inimigo não fica num lugar só, e não aparece sempre no mesmo quadro. O recorte foi refeito para lidar com isso:
- **Camadas:** o corpo fica no plano A. Partes animadas (a espada do Centaur, os fantasmas) são sprites. Os chefes enormes (formas do Dark Force) ficam no plano B. O recorte junta as três camadas, na posição da tela, usando só os tiles reservados pelo carregador: de 407 (depois dos do grupo) até `FFEE54`/32.
- **Fase 1, sem apertar nada (300 quadros):** escolhe o primeiro quadro com pelo menos 90% das células do inimigo nos planos. Muitos começam inteiros no plano A e, quando a animação de espera começa, o jogo apaga parte das células e passa a desenhá-las como sprite. Por isso um quadro fixo cortava metade do Centaur.
- **Paleta:** a mais clara entre esse quadro e o fim da fase. Os chefes finais entram no escuro.
- **Fase 2:** se a fase 1 só mostrou nada, uma silhueta ou uma nuvem de uma cor, aperta C a cada 40 quadros para o turno andar. Escolhe o quadro com mais pixels vezes cores. Os efeitos do ataque do Chaz ficam de fora porque a faixa passa a começar no menor tile do inimigo nos planos. É assim que aparecem os fantasmas (106-108), o Dimensworm e as formas do Dark Force (formações 9, 17 e 26).
- **HP do Chaz:** 999, para a batalha não acabar em derrota.

São **153 inimigos** (IDs 0-152, o tamanho da tabela de gráficos). Depois do 152, a lista de nomes continua com nomes de ataques (LASRCANNON, FIREBREATH…). Os IDs 129-133 são as formas do Dark Force e saem certos nas formações fixas 9, 10, 17, 18 e 26. Os IDs 134 e 135 não estão em nenhuma formação e, carregados sozinhos, mostram lixo.

### Técnicas e skills (`emu/technique_gifs.py` → `assets/techniques/`)

Os gráficos dos efeitos são listas de tiles Nemesis: tabelas `0x27E88A` (289 listas) e `0x27EA66`, carregadas por `0x41880` em `0xB78E`/`0xB7A0`. Cada lista tem a quantidade − 1 e depois os ponteiros, descomprimidos em sequência na VRAM. Os quadros são montados em sprites, com paleta própria, então soltos não formam imagem.

O script grava cada uma sendo usada na batalha:
1. põe a técnica no 1º slot (`+0x52`) ou a skill no 1º slot de skill (`+0x62`, usos 9/9 em `+0x6A`), com HP/TP 999;
2. no menu de ícones (atacar, técnica, skill, item, defender): C, direita 1× ou 2×, C, C e C;
3. grava 240 quadros e salva GIF e folha.

Nomes na lista `0x2AAFB4`: técnica t = índice 159+t (o Chaz começa com a 24, RES), skill s = índice 199+s. São 40 técnicas e 54 skills. RYUKA e HINAS são só de campo. 15 skills não animam com o Chaz sozinho. Com o argumento `testar`, o grupo vira Chaz + outro personagem: o Chaz defende e o outro usa a skill. Sozinho no grupo, outro personagem deixa o menu preso no COMD.

## Menus e telas fixas

- **Figuras da tela de status** (`tools/export_misc_graphics.py` → `assets/menus/status_*`): rotina `0x5CE60`, tabela `0x5D548` (um Nemesis por personagem, no tile `0x580`) e `0x5D574` (mapa de 10×10, 200 bytes por personagem), linha de paleta 2. São 11.
- **Retratos das lojas** (`assets/menus/loja_*`): tabela `0x68006`, 6×6 tiles como os do diálogo; 8 distintos.
- **Veículos** (`assets/menus/veiculo_*`): tabela `0x51AA6`, três folhas em quadros de 2×4. A paleta não foi confirmada.
- **Abertura e título** (`emu/boot_screens.py` → `assets/screens/`): o jogo ligado sem apertar nada por uma volta da apresentação (SEGA, prólogo "The long, long struggle…", título e a sequência com os personagens). Grava cada tela com mais de 5% de diferença para a anterior.
- **Inventário Nemesis** (`tools/nemesis_inventory.py` → `assets/nemesis_scan/inventario.csv`): para cada um dos 834 fluxos, a categoria, quem o referencia e onde está a extração com cor.
  - 822 têm uso identificado.
  - Sem extração própria, só em tons de cinza: 24 de cenas e eventos, 12 de menus, 15 da interface de batalha, 8 da abertura e 12 sem uso conhecido.

### Cenários de batalha (`tools/export_battle_backgrounds.py` → `assets/battle_backgrounds/`)

A rotina `0x6BFC` escolhe o cenário:
- **batalha fixa:** tabela `0x6C8C`, indexada pela formação;
- **mapa diferente de 0:** tabela `0x6CA8`, indexada pelo mapa (`FF` = sem encontro);
- **Motavia:** o tipo de terreno em `FFECEF`. O cenário 4 vira 5 com a flag `0x9E`.

Cada cenário é um registro de 12 bytes em `0x6ED4`: tiles Nemesis, mapa Enigma de 64×24 células e paleta de 13 cores. São 32: deserto, praia, campo, mar, montanhas de Dezolis, naves, masmorras, cavernas, florestas etc. `backgrounds.csv` lista os mapas e as batalhas fixas que usam cada um.

## Personagens (`assets/party/`, `assets/portraits/`)

- **Sprites de campo** (`tools/export_party_sprites.py`): a tabela `0x5E732` tem um ponteiro por personagem para folhas **sem compressão** de `0x900` bytes em `0x290000`. Cada folha tem 72 tiles = 9 quadros de 2×4 tiles; o jogo copia para a VRAM só o quadro da vez. A paleta (linha 2) vem logo depois, em `0x296300`. A tabela foi achada procurando na ROM os tiles que estavam na VRAM com o grupo andando.
- **Sprites de batalha** (`emu/party_battle.py`): o script põe os personagens no grupo (`FFF40A`, copiando a ficha do Chaz para os vazios) antes do encontro e recorta cada um do plano A. Na tela, a ordem das posições da esquerda para a direita é 4º, 2º, 1º, 3º e 5º membro.
- **Retratos** (`tools/export_portraits.py`): o controle de texto `F4 n` (tratador `0x69C42`) descomprime o retrato n da tabela `0x6A4B0` no tile `0x55C` e desenha 6×6 células com o mapa fixo `0x2A2B36`, na linha de paleta 2. São 39 retratos.

## Quadros das cenas (`tools/export_panels.py` → `assets/panels/`)

O controle `F2 00 hhll` abre um quadro ilustrado (`0x6AF9C`). `0x6B290` acha o registro: a tabela `0x6B2B6` tem 7 ponteiros, um por grupo de 64 IDs, e cada registro tem 30 bytes:
- tile de destino na VRAM e ponteiro Nemesis;
- largura e altura, coluna e linha na tela;
- atributo base, paleta e mapa Enigma da primeira camada;
- os mesmos três campos para uma segunda camada (`FFFF` = não tem).

O script carrega os gráficos de cada grupo em ordem, como numa cena, e desenha a segunda camada por baixo da primeira. Saíram **310 quadros**; os 163 citados no diálogo estão entre eles (`panels.csv`).

## Sprites de mapa (`emu/dump_sprites.py` → `assets/sprites/`)

São os NPCs e objetos de cada mapa, tirados do próprio registro. As folhas saem em quadros de 2×4 tiles (16×32 px, em colunas, como na tabela de sprites do VDP), com a linha de paleta que o sprite usa na tela depois do carregamento. Saíram 116 conjuntos. Em 20 a paleta foi confirmada por um sprite visível (`paleta_confirmada`); nos outros foi usada a linha 3. Os personagens jogáveis não estão aqui: ver Personagens.

## Compressão

Os três formatos padrão da Sega, reimplementados em [`tools/sega_codecs.py`](tools/sega_codecs.py).

| Rotina | Formato | Uso |
|---|---|---|
| `0x41BEA` | Kosinski | tilesets de mapa, blocos, layouts, diálogo, tabelas |
| `0x41A90` | Enigma | mapas de tiles de telas fixas, quadros das cenas, cenários de batalha |
| `0x41752` / `0x41740` | Nemesis | sprites, retratos, fontes |

A validação foi feita de três formas:
- **Encadeamento:** cada recurso termina onde começa o seguinte (por exemplo, `1CC47A` + 2.608 = `1CCEAA`).
- **VRAM:** o Nemesis bate byte a byte com a VRAM de cenas reais (fonte `2A303A` 87/87, sprite `121600` 72/72).
- **Enigma com tile base:** o valor base entra também nos valores lidos em linha, como no descompressor do jogo. Sem isso, a segunda camada dos quadros das cenas saía com tiles fora do lugar.
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
- **Formato SMPS** (`tools/export_smps.py` → `smps_songs.csv`, `smps_voices.csv`), confirmado pelo rastreio do que o driver lê:
  - tabela de músicas em `0xD1C40` (ponteiro de 32 bits por ID, a partir de `0x81`);
  - cabeçalho: deslocamento dos instrumentos, nº de trilhas FM (a primeira é o DAC) e PSG, divisor e andamento; depois as trilhas (deslocamento, transposição, volume e, no PSG, modulação e instrumento);
  - instrumento FM de 25 bytes;
  - comandos: `00`-`7F` duração, `80` pausa, `81`-`DF` nota, `E0`-`FF` controle pela tabela de saltos `0xD1038`. `EE n` escolhe o sample do DAC, `F8`/`F9` chamam e retornam, `F7` repete, `F6` salta e `F2` encerra. O destino dos saltos é o endereço do 2º byte do argumento mais o deslocamento com sinal.
  - Saíram 52 músicas e seus instrumentos.
- **Samples** (`tools/extract_samples.py`): 17 samples em `0x0E0000`-`0x0FFFFF`, contíguos. Todos são usados.
  - `tools/sample_usage.py` executa a trilha de DAC de cada música e conta, por sample, os casos de taxa das notas (`sample_usage.csv`). Os WAV são regravados com a taxa mais usada, de 4.554 Hz (`87`) a 10.227 Hz (`83`, `89`, `8C`, `91`).
  - Um teste no Z80 do emulador tocou os 8 samples que não apareciam nos VGMs e as escritas no DAC bateram com o PCM extraído.
  - `tools/sample_rates_from_vgm.py` mede a mediana nos VGMs. Ela coincide com a tabela onde o sample toca quase sempre numa taxa (`81`, `82`, `88`, `8E`, `91`) e mistura taxas nos outros.

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
| Batalhas naturais em todos os mapas com zona de encontro (`emu/battle_session.py`) | 29.386 instruções executadas no total; **3.968 funções** |
| Correções de início de função | `Battle_GiveRewards` (`0x303A` → `0x300A`) e `Field_ChestMesetaReward` (`0x66C72` → `0x66C6A`) |

`export/read_only_code.csv` lista as 67 instruções que o Ghidra trata como código, mas o jogo só leu como dado (tabelas embutidas no meio do código).

## Limites conhecidos

- **Inimigos:** um quadro por inimigo; as animações de ataque deles não foram gravadas. O Outerbeast (74) sai só com o portal de onde surge. Os IDs 134 e 135 não têm imagem válida.
- **Gráficos sem cor:** 71 fluxos Nemesis de cenas, menus, interface e abertura só existem em tons de cinza (ver o inventário). O final do jogo não foi gravado.
- **Dezolis:** debaixo de parte das montanhas aparecem blocos marrons da camada de baixo que na tela real ficam cobertos de neve. O plano B do jogo não bate com os blocos da tabela nesses pontos.
- **Personagens:** os sprites de batalha recortados são a pose de costas parada; os golpes aparecem nos GIFs de técnicas e skills.
- **Técnicas e skills:** WARLA e MEDICE (apoio) não mostraram efeito na tela, nem com o Chaz nem com a Rune; RYUKA e HINAS são só de campo.
- **Campos sem nome:**
  - nos inimigos: `campo_12`, `campo_14`, `ia_extra` e o significado de cada byte de resistência;
  - nos níveis: o significado exato dos 2 IDs `aprende_*`;
  - nos itens: o significado exato das máscaras e dos dois bytes de bônus.
- **Música:** VGM e MIDI saem da execução do driver. Não há conversor das sequências SMPS para MIDI, só o leitor de estrutura e o interpretador da trilha de DAC.
- **Eventos:** as 20 chamadas de flag com o número em registrador.
- **Sprites:** 96 dos 116 conjuntos de sprite usam uma paleta suposta (linha 3).
