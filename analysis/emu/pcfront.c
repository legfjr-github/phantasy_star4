/* Frontend sem tela do Genesis Plus GX para análise no PC (DLL controlada por Python/ctypes).
 * Roda quadros com entrada de controle, expõe a memória do VDP e do 68000, salva/carrega estado
 * em memória e registra as escritas no YM2612 e no PSG (para gerar VGM). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "libretro.h"
#include "shared.h"
#include "cpuhook.h"

#define EXPORT __declspec(dllexport)

/* ---- rastreio: marca cada byte da ROM lido (bit 0) ou executado (bit 1) pelo 68000 */
static unsigned char rom_marks[0x400000];
static unsigned int vram_writes, last_pc;

/* watch de escrita: registra (PC, endereço, valor) quando o 68000 grava em [watch_lo, watch_hi) */
static unsigned int watch_lo, watch_hi, watch_len;
static unsigned int watch_log[4096][3];

static void trace_hook(hook_type_t type, int width, unsigned int address, unsigned int value)
{
   unsigned int a = address & 0xFFFFFF, i;
   if (type == HOOK_VRAM_W) { vram_writes++; return; }
   if (type == HOOK_M68K_W && a >= watch_lo && a < watch_hi && watch_len < 4096) {
      watch_log[watch_len][0] = last_pc;
      watch_log[watch_len][1] = a;
      watch_log[watch_len][2] = value;
      watch_len++;
   }
   if (type == HOOK_M68K_E) last_pc = a;
   if (a >= sizeof(rom_marks)) return;
   if (type == HOOK_M68K_E) rom_marks[a] |= 2;
   else if (type == HOOK_M68K_R)
      for (i = 0; i < (unsigned)width && a + i < sizeof(rom_marks); i++) rom_marks[a + i] |= 1;
}

EXPORT void ps_trace(int on) { set_cpu_hook(on ? trace_hook : NULL); }
EXPORT void ps_trace_clear(void) { memset(rom_marks, 0, sizeof(rom_marks)); vram_writes = 0; }
EXPORT unsigned char *ps_trace_marks(void) { return rom_marks; }
EXPORT unsigned int ps_trace_vram_writes(void) { return vram_writes; }
EXPORT void ps_watch(unsigned int lo, unsigned int hi) { watch_lo = lo & 0xFFFFFF; watch_hi = hi & 0xFFFFFF; watch_len = 0; }
EXPORT unsigned int ps_watch_len(void) { return watch_len; }
EXPORT unsigned int *ps_watch_log(void) { return &watch_log[0][0]; }

/* ROM carregada, para patches em memória (palavras em little-endian, como a RAM). */
EXPORT unsigned char *ps_rom(void) { return cart.rom; }

/* reg, vram, cram, vsram, work_ram, zram, cart e fm_write vêm de shared.h. */
void psg_write_real(unsigned int clocks, unsigned int data);

static char sys_dir[512];
static unsigned short frame[720 * 576];
static unsigned frame_w = 320, frame_h = 224;
static int input_mask;
static struct retro_system_av_info av;

/* ---- registro de escritas de som: (quadro, ciclos no quadro, tipo, endereço, dado) */
typedef struct { unsigned int frame, cycles; unsigned char kind, addr, data, pad; } SoundWrite;
static SoundWrite *log_buf;
static unsigned int log_len, log_cap, frame_no;
static int logging;
static unsigned char fm_latch[2];
static void (*fm_write_orig)(unsigned int, unsigned int, unsigned int);

static void log_push(unsigned int cycles, int kind, int addr, int data)
{
   if (!logging) return;
   if (log_len == log_cap) {
      log_cap = log_cap ? log_cap * 2 : 1 << 16;
      log_buf = realloc(log_buf, log_cap * sizeof(SoundWrite));
   }
   log_buf[log_len].frame = frame_no;
   log_buf[log_len].cycles = cycles;
   log_buf[log_len].kind = (unsigned char)kind;
   log_buf[log_len].addr = (unsigned char)addr;
   log_buf[log_len].data = (unsigned char)data;
   log_len++;
}

/* address: 0/2 = latch de registrador da porta 0/1, 1/3 = dado. kind 0 = porta 0, 1 = porta 1. */
static void fm_write_log(unsigned int cycles, unsigned int address, unsigned int data)
{
   int port = (address >> 1) & 1;
   if (address & 1) log_push(cycles, port, fm_latch[port], data);
   else fm_latch[port] = (unsigned char)data;
   fm_write_orig(cycles, address, data);
}

void psg_write(unsigned int clocks, unsigned int data)
{
   log_push(clocks, 2, 0, data);
   psg_write_real(clocks, data);
}

static void hook_fm(void)
{
   if (fm_write != fm_write_log) {
      fm_write_orig = fm_write;
      fm_write = fm_write_log;
   }
}

/* ---- callbacks libretro */
static void front_log(enum retro_log_level level, const char *fmt, ...)
{
   va_list ap;
   if (level < RETRO_LOG_WARN) return;
   va_start(ap, fmt);
   vfprintf(stderr, fmt, ap);
   va_end(ap);
}

static bool env_cb(unsigned cmd, void *data)
{
   switch (cmd) {
      case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
      case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
         *(const char **)data = sys_dir;
         return true;
      case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
         return *(enum retro_pixel_format *)data == RETRO_PIXEL_FORMAT_RGB565;
      case RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
         ((struct retro_log_callback *)data)->log = front_log;
         return true;
      case RETRO_ENVIRONMENT_GET_INPUT_BITMASKS:
      case RETRO_ENVIRONMENT_GET_CAN_DUPE:
         if (cmd == RETRO_ENVIRONMENT_GET_CAN_DUPE) *(bool *)data = true;
         return true;
      default:
         return false;
   }
}

static void video_cb(const void *data, unsigned w, unsigned h, size_t pitch)
{
   unsigned y;
   if (!data || w > 720 || h > 576) return;
   for (y = 0; y < h; y++)
      memcpy(frame + y * w, (const unsigned char *)data + y * pitch, w * 2);
   frame_w = w;
   frame_h = h;
}

static size_t audio_batch_cb(const int16_t *data, size_t frames) { return frames; }
static void audio_cb(int16_t l, int16_t r) {}
static void input_poll_cb(void) {}

static int16_t input_state_cb(unsigned port, unsigned device, unsigned index, unsigned id)
{
   if (port != 0 || device != RETRO_DEVICE_JOYPAD) return 0;
   if (id == RETRO_DEVICE_ID_JOYPAD_MASK) return (int16_t)input_mask;
   return (input_mask >> id) & 1;
}

/* ---- API exportada */
EXPORT int ps_load(const char *rom, const char *dir)
{
   struct retro_game_info info = { 0 };
   snprintf(sys_dir, sizeof(sys_dir), "%s", dir);
   retro_set_environment(env_cb);
   retro_set_video_refresh(video_cb);
   retro_set_audio_sample(audio_cb);
   retro_set_audio_sample_batch(audio_batch_cb);
   retro_set_input_poll(input_poll_cb);
   retro_set_input_state(input_state_cb);
   retro_init();
   info.path = rom;
   if (!retro_load_game(&info)) return 0;
   retro_get_system_av_info(&av);
   retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD);
   hook_fm();
   return 1;
}

/* Roda n quadros com a entrada dada (bits libretro: B=0, A(Y)=1, START=3, cima=4, baixo=5,
 * esquerda=6, direita=7, C(A)=8). */
EXPORT void ps_run(int n, int mask)
{
   input_mask = mask;
   while (n-- > 0) {
      hook_fm();
      retro_run();
      frame_no++;
   }
}

EXPORT unsigned char *ps_mem(int which, int *size)
{
   switch (which) {
      case 0: *size = sizeof(vram); return vram;
      case 1: *size = sizeof(cram); return cram;
      case 2: *size = sizeof(vsram); return vsram;
      case 3: *size = sizeof(reg); return reg;
      case 4: *size = sizeof(work_ram); return work_ram;
      case 5: *size = sizeof(zram); return zram;
      case 6: *size = frame_w * frame_h * 2; return (unsigned char *)frame;
      default: *size = 0; return NULL;
   }
}

EXPORT int ps_frame_size(void) { return (int)(frame_w << 16 | frame_h); }

EXPORT int ps_state_size(void) { return (int)retro_serialize_size(); }
EXPORT int ps_save_state(void *buf, int size) { return retro_serialize(buf, size); }
EXPORT int ps_load_state(const void *buf, int size) { int ok = retro_unserialize(buf, size); hook_fm(); return ok; }

EXPORT void ps_log_start(void) { log_len = 0; logging = 1; }
EXPORT void ps_log_stop(void) { logging = 0; }
EXPORT unsigned int ps_log_len(void) { return log_len; }
EXPORT void *ps_log_buf(void) { return log_buf; }
EXPORT unsigned int ps_frame_no(void) { return frame_no; }
EXPORT double ps_fps(void) { return av.timing.fps; }
