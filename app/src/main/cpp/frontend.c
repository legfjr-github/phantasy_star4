/* Frontend libretro mínimo: liga o núcleo Genesis Plus GX à camada Java via JNI. */
#include <jni.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <android/log.h>
#include "libretro.h"

#define TAG "psemu"
#define MAX_W 720
#define MAX_H 576
#define AUDIO_MAX 8192

static char sys_dir[512];
static uint16_t frame[MAX_W * MAX_H];
static unsigned frame_w = 320, frame_h = 224;
static int16_t audio_buf[AUDIO_MAX];
static size_t audio_len;
static int16_t input_mask;
static struct retro_system_av_info av;

static void log_cb(enum retro_log_level level, const char *fmt, ...)
{
   va_list ap;
   va_start(ap, fmt);
   __android_log_vprint(level >= RETRO_LOG_WARN ? ANDROID_LOG_WARN : ANDROID_LOG_INFO, TAG, fmt, ap);
   va_end(ap);
}

static bool env_cb(unsigned cmd, void *data)
{
   switch (cmd)
   {
      case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
      case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
         *(const char **)data = sys_dir;
         return true;
      case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
         return *(enum retro_pixel_format *)data == RETRO_PIXEL_FORMAT_RGB565;
      case RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
         ((struct retro_log_callback *)data)->log = log_cb;
         return true;
      case RETRO_ENVIRONMENT_GET_INPUT_BITMASKS:
         return true;
      case RETRO_ENVIRONMENT_GET_CAN_DUPE:
         *(bool *)data = true;
         return true;
      default:
         return false;
   }
}

static void video_cb(const void *data, unsigned w, unsigned h, size_t pitch)
{
   unsigned y;
   if (!data || w > MAX_W || h > MAX_H)
      return;
   for (y = 0; y < h; y++)
      memcpy(frame + y * w, (const uint8_t *)data + y * pitch, w * 2);
   frame_w = w;
   frame_h = h;
}

static size_t audio_batch_cb(const int16_t *data, size_t frames)
{
   size_t n = frames * 2;
   if (audio_len + n > AUDIO_MAX)
      n = AUDIO_MAX - audio_len;
   memcpy(audio_buf + audio_len, data, n * 2);
   audio_len += n;
   return frames;
}

static void audio_cb(int16_t l, int16_t r)
{
   int16_t s[2] = { l, r };
   audio_batch_cb(s, 1);
}

static void input_poll_cb(void) {}

static int16_t input_state_cb(unsigned port, unsigned device, unsigned index, unsigned id)
{
   if (port != 0 || device != RETRO_DEVICE_JOYPAD)
      return 0;
   if (id == RETRO_DEVICE_ID_JOYPAD_MASK)
      return input_mask;
   return (input_mask >> id) & 1;
}

static int write_file(const char *path, const void *data, size_t size)
{
   FILE *f = fopen(path, "wb");
   if (!f)
      return 0;
   fwrite(data, 1, size, f);
   fclose(f);
   return 1;
}

static size_t read_file(const char *path, void *data, size_t size)
{
   size_t n;
   FILE *f = fopen(path, "rb");
   if (!f)
      return 0;
   n = fread(data, 1, size, f);
   fclose(f);
   return n;
}

#define FN(name) Java_br_emu_ps4_Native_##name

JNIEXPORT jboolean JNICALL FN(loadGame)(JNIEnv *env, jclass c, jstring jdir, jstring jrom)
{
   struct retro_game_info info = { 0 };
   const char *dir = (*env)->GetStringUTFChars(env, jdir, NULL);
   const char *rom = (*env)->GetStringUTFChars(env, jrom, NULL);
   bool ok;

   snprintf(sys_dir, sizeof(sys_dir), "%s", dir);
   retro_set_environment(env_cb);
   retro_set_video_refresh(video_cb);
   retro_set_audio_sample(audio_cb);
   retro_set_audio_sample_batch(audio_batch_cb);
   retro_set_input_poll(input_poll_cb);
   retro_set_input_state(input_state_cb);
   retro_init();

   info.path = rom;
   ok = retro_load_game(&info);
   if (ok)
   {
      retro_get_system_av_info(&av);
      retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD);
   }
   (*env)->ReleaseStringUTFChars(env, jdir, dir);
   (*env)->ReleaseStringUTFChars(env, jrom, rom);
   return ok;
}

JNIEXPORT void JNICALL FN(unloadGame)(JNIEnv *env, jclass c)
{
   retro_unload_game();
   retro_deinit();
}

/* Roda um quadro; copia o vídeo para o buffer direto e devolve o número de amostras de áudio. */
JNIEXPORT jint JNICALL FN(runFrame)(JNIEnv *env, jclass c, jobject video, jshortArray audio)
{
   jint n;
   audio_len = 0;
   retro_run();
   memcpy((*env)->GetDirectBufferAddress(env, video), frame, frame_w * frame_h * 2);
   n = (jint)audio_len;
   if (n > (*env)->GetArrayLength(env, audio))
      n = (*env)->GetArrayLength(env, audio);
   (*env)->SetShortArrayRegion(env, audio, 0, n, audio_buf);
   return n;
}

JNIEXPORT jint JNICALL FN(frameWidth)(JNIEnv *env, jclass c) { return frame_w; }
JNIEXPORT jint JNICALL FN(frameHeight)(JNIEnv *env, jclass c) { return frame_h; }
JNIEXPORT jdouble JNICALL FN(fps)(JNIEnv *env, jclass c) { return av.timing.fps; }
JNIEXPORT jint JNICALL FN(sampleRate)(JNIEnv *env, jclass c) { return (jint)av.timing.sample_rate; }
JNIEXPORT void JNICALL FN(setInput)(JNIEnv *env, jclass c, jint mask) { input_mask = (int16_t)mask; }

JNIEXPORT void JNICALL FN(saveSram)(JNIEnv *env, jclass c, jstring jpath)
{
   const char *path = (*env)->GetStringUTFChars(env, jpath, NULL);
   size_t size = retro_get_memory_size(RETRO_MEMORY_SAVE_RAM);
   void *data = retro_get_memory_data(RETRO_MEMORY_SAVE_RAM);
   if (data && size)
      write_file(path, data, size);
   (*env)->ReleaseStringUTFChars(env, jpath, path);
}

JNIEXPORT void JNICALL FN(loadSram)(JNIEnv *env, jclass c, jstring jpath)
{
   const char *path = (*env)->GetStringUTFChars(env, jpath, NULL);
   size_t size = retro_get_memory_size(RETRO_MEMORY_SAVE_RAM);
   void *data = retro_get_memory_data(RETRO_MEMORY_SAVE_RAM);
   if (data && size)
      read_file(path, data, size);
   (*env)->ReleaseStringUTFChars(env, jpath, path);
}

JNIEXPORT jboolean JNICALL FN(saveState)(JNIEnv *env, jclass c, jstring jpath)
{
   const char *path = (*env)->GetStringUTFChars(env, jpath, NULL);
   size_t size = retro_serialize_size();
   void *data = malloc(size);
   jboolean ok = data && retro_serialize(data, size) && write_file(path, data, size);
   free(data);
   (*env)->ReleaseStringUTFChars(env, jpath, path);
   return ok;
}

JNIEXPORT jboolean JNICALL FN(loadState)(JNIEnv *env, jclass c, jstring jpath)
{
   const char *path = (*env)->GetStringUTFChars(env, jpath, NULL);
   size_t size = retro_serialize_size();
   void *data = malloc(size);
   jboolean ok = data && read_file(path, data, size) == size && retro_unserialize(data, size);
   free(data);
   (*env)->ReleaseStringUTFChars(env, jpath, path);
   return ok;
}

/* Memória do VDP e RAM do 68000, como o núcleo guarda (palavras em little-endian). */
extern uint8_t reg[0x20], vram[0x10000], cram[0x80], vsram[0x80], work_ram[0x10000];

JNIEXPORT jboolean JNICALL FN(dumpVideo)(JNIEnv *env, jclass c, jstring jdir)
{
   char path[600];
   const char *dir = (*env)->GetStringUTFChars(env, jdir, NULL);
   int ok = 1;
#define DUMP(name, buf) snprintf(path, sizeof(path), "%s/" name, dir); ok &= write_file(path, buf, sizeof(buf))
   DUMP("vram.bin", vram);
   DUMP("cram.bin", cram);
   DUMP("vsram.bin", vsram);
   DUMP("vdpreg.bin", reg);
   DUMP("wram.bin", work_ram);
#undef DUMP
   snprintf(path, sizeof(path), "%s/frame.raw", dir);
   ok &= write_file(path, frame, frame_w * frame_h * 2);
   snprintf(path, sizeof(path), "%s/frame.txt", dir);
   {
      char info[32];
      int n = snprintf(info, sizeof(info), "%u %u\n", frame_w, frame_h);
      ok &= write_file(path, info, n);
   }
   (*env)->ReleaseStringUTFChars(env, jdir, dir);
   return ok;
}

JNIEXPORT void JNICALL FN(cheatReset)(JNIEnv *env, jclass c) { retro_cheat_reset(); }

JNIEXPORT void JNICALL FN(cheatSet)(JNIEnv *env, jclass c, jint index, jstring jcode)
{
   const char *code = (*env)->GetStringUTFChars(env, jcode, NULL);
   retro_cheat_set(index, true, code);
   (*env)->ReleaseStringUTFChars(env, jcode, code);
}
