cmake_minimum_required(VERSION 3.22)
project(psemu C)

set(G ${CMAKE_CURRENT_SOURCE_DIR}/gpgx)
set(LC ${G}/libretro/libretro-common)

set(CORE_DIRS
    ${G}/core ${G}/core/z80 ${G}/core/m68k ${G}/core/ntsc ${G}/core/sound
    ${G}/core/sound/minimp3 ${G}/core/input_hw ${G}/core/cd_hw
    ${G}/core/cart_hw ${G}/core/cart_hw/svp)

set(CORE_SRC "")
foreach(d ${CORE_DIRS})
    file(GLOB s ${d}/*.c)
    list(APPEND CORE_SRC ${s})
endforeach()

list(APPEND CORE_SRC
    ${LC}/streams/file_stream.c
    ${LC}/streams/file_stream_transforms.c
    ${LC}/compat/fopen_utf8.c
    ${LC}/compat/compat_snprintf.c
    ${LC}/compat/compat_strl.c
    ${LC}/compat/compat_strcasestr.c
    ${LC}/compat/compat_posix_string.c
    ${LC}/encodings/encoding_utf.c
    ${LC}/file/file_path.c
    ${LC}/file/retro_dirent.c
    ${LC}/lists/string_list.c
    ${LC}/lists/dir_list.c
    ${LC}/memmap/memalign.c
    ${LC}/string/stdstring.c
    ${LC}/vfs/vfs_implementation.c
    ${G}/libretro/deps/zlib-1.2.11/adler32.c
    ${G}/libretro/deps/zlib-1.2.11/crc32.c
    ${G}/libretro/deps/zlib-1.2.11/inffast.c
    ${G}/libretro/deps/zlib-1.2.11/inflate.c
    ${G}/libretro/deps/zlib-1.2.11/inftrees.c
    ${G}/libretro/deps/zlib-1.2.11/zutil.c
    ${G}/libretro/libretro.c)

add_library(psemu SHARED ${CORE_SRC} frontend.c)

target_include_directories(psemu PRIVATE
    ${CORE_DIRS} ${G}/libretro ${LC}/include ${G}/libretro/deps/zlib-1.2.11)

target_compile_definitions(psemu PRIVATE
    "INLINE=static inline" USE_16BPP_RENDERING LSB_FIRST BYTE_ORDER=LITTLE_ENDIAN
    __LIBRETRO__ FRONTEND_SUPPORTS_RGB565 ALIGN_LONG ALIGN_WORD
    M68K_OVERCLOCK_SHIFT=20 Z80_OVERCLOCK_SHIFT=20 HAVE_YM3438_CORE
    USE_LIBRETRO_VFS HAVE_OPLL_CORE USE_PER_SOUND_CHANNELS_CONFIG
    MAXROMSIZE=16777216)

target_compile_options(psemu PRIVATE -O2 -ffast-math -funroll-loops -w)
target_link_libraries(psemu log GLESv2 android)
