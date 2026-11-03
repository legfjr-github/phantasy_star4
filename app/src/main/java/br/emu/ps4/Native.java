package br.emu.ps4;

import java.nio.ByteBuffer;

/** Ponte JNI para o frontend libretro em frontend.c. */
public final class Native {
    static { System.loadLibrary("psemu"); }

    // Bits do joypad libretro, já no mapeamento do Genesis Plus GX (Y=A, B=B, A=C).
    public static final int BTN_B = 1;
    public static final int BTN_A = 1 << 1;
    public static final int BTN_START = 1 << 3;
    public static final int BTN_UP = 1 << 4;
    public static final int BTN_DOWN = 1 << 5;
    public static final int BTN_LEFT = 1 << 6;
    public static final int BTN_RIGHT = 1 << 7;
    public static final int BTN_C = 1 << 8;

    public static native boolean loadGame(String systemDir, String romPath);
    public static native void unloadGame();
    public static native int runFrame(ByteBuffer video, short[] audio);
    public static native int frameWidth();
    public static native int frameHeight();
    public static native double fps();
    public static native int sampleRate();
    public static native void setInput(int mask);
    public static native void saveSram(String path);
    public static native void loadSram(String path);
    public static native boolean saveState(String path);
    public static native boolean loadState(String path);
    public static native boolean dumpVideo(String dir);
    public static native void cheatReset();
    public static native void cheatSet(int index, String code);

    private Native() {}
}
