# PS4 Mobile

App Android dedicado para jogar Phantasy Star IV (Mega Drive) a partir da sua própria cópia da ROM, mais as ferramentas de análise da ROM.

A ROM e nenhum conteúdo extraído dela fazem parte deste repositório. O app pede o arquivo na primeira execução.

## App (`app/`)

- Núcleo [Genesis Plus GX](https://github.com/libretro/Genesis-Plus-GX), submódulo em `app/src/main/cpp/gpgx`, com um frontend libretro próprio em C (`frontend.c`, JNI).
- Upscale por OpenGL ES: pixel nítido em escala inteira ou em tela cheia, CRT e suave.
- Controles por toque e por gamepad, velocidade 1x a 4x, 5 slots de save state e save do cartucho automático.
- 93 códigos Game Genie com checkbox, em categorias, e campo para códigos livres.
- Menu "Exportar gráficos (análise)", que despeja a VRAM, a CRAM e a RAM para uso com `analysis/tools/render_vdp.py`.

Build (JDK 17+, Android SDK 35, NDK 27.2, CMake 3.22):

```
git clone --recursive https://github.com/legfjr-github/phantasy_star4.git
gradlew assembleDebug
```

## Análise (`analysis/`)

Scripts do Ghidra e ferramentas em Python para a ROM USA (SHA-1 `BC7FF6D6A8408F38562BC610F24645CAD6C42629`): mapa de memória, rotinas nomeadas, descompressores Kosinski, Enigma e Nemesis, driver de som Z80 e formato do texto. Os detalhes estão em [`analysis/README.md`](analysis/README.md).

Os scripts geram em `analysis/assets/` os gráficos, os sons e o texto extraídos da sua ROM. Essa pasta fica fora do git.
