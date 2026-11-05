package br.emu.ps4;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.Toast;

import java.io.File;
import java.text.DateFormat;
import java.util.Date;

public class GameActivity extends Activity implements ControlsView.Listener {
    private GLSurfaceView surface;
    private GameRenderer renderer;
    private ControlsView controls;
    private static final int SLOTS = 5;
    private File sram, autoState;
    private int keyMask, axisMask;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        File dir = getFilesDir();
        sram = new File(dir, "rom.srm");
        if (!Native.loadGame(dir.getAbsolutePath(), new File(dir, MainActivity.ROM_NAME).getAbsolutePath())) {
            Toast.makeText(this, "Não foi possível carregar a ROM", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        Native.loadSram(sram.getAbsolutePath());
        applyCheats();

        SharedPreferences p = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE);
        // Volta exatamente de onde parou, mesmo se o Android tiver recriado a tela.
        autoState = new File(dir, MainActivity.AUTO_STATE);
        if (p.getBoolean("resume", true) && autoState.exists()) Native.loadState(autoState.getAbsolutePath());
        renderer = new GameRenderer(p.getInt("video", GameRenderer.MODE_SHARP), p.getBoolean("stretch", false));
        surface = new GLSurfaceView(this);
        surface.setEGLContextClientVersion(2);
        surface.setRenderer(renderer);
        controls = new ControlsView(this, this);

        FrameLayout root = new FrameLayout(this);
        root.addView(surface);
        root.addView(controls);
        setContentView(root);
        hideSystemUi();
    }

    private void applyCheats() {
        Native.cheatReset();
        SharedPreferences p = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE);
        int i = 0;
        for (Cheats.Cheat ch : Cheats.ALL)
            if (p.getBoolean(ch.key(), false)) Native.cheatSet(i++, ch.code);
        String codes = p.getString("cheats", "");
        for (String line : codes.split("\n")) {
            String code = line.trim();
            if (code.isEmpty() || code.startsWith("#")) continue;
            Native.cheatSet(i++, code.toUpperCase());
        }
    }

    private void hideSystemUi() {
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
    }

    @Override
    public void onInput(int mask) { Native.setInput(mask); }

    @Override
    public void onSpeed(int speed) { renderer.setSpeed(speed); }

    @Override
    public void onMenu() {
        renderer.setPaused(true);
        new AlertDialog.Builder(this)
                .setItems(new String[]{"Salvar estado", "Carregar estado", "Continuar", "Exportar gráficos (análise)", "Sair"}, (d, which) -> {
                    if (which == 0) pickSlot(true);
                    else if (which == 1) pickSlot(false);
                    else if (which == 3) dumpVideo();
                    else if (which == 4) finish();
                    else resume();
                })
                .setOnCancelListener(d -> resume())
                .show();
    }

    private File slotFile(int slot) { return new File(getFilesDir(), "state" + slot + ".sav"); }

    private void pickSlot(boolean save) {
        String[] items = new String[SLOTS];
        DateFormat fmt = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT);
        for (int i = 0; i < SLOTS; i++) {
            File f = slotFile(i + 1);
            items[i] = "Slot " + (i + 1) + "  " + (f.exists() ? fmt.format(new Date(f.lastModified())) : "(vazio)");
        }
        new AlertDialog.Builder(this)
                .setTitle(save ? "Salvar em" : "Carregar de")
                .setItems(items, (d, which) -> {
                    String path = slotFile(which + 1).getAbsolutePath();
                    String slot = "slot " + (which + 1);
                    renderer.runOnEmuThread(save
                            ? () -> toast(Native.saveState(path) ? "Salvo no " + slot : "Falha ao salvar")
                            : () -> toast(Native.loadState(path) ? "Carregado do " + slot : slot + " vazio"));
                    resume();
                })
                .setOnCancelListener(d -> resume())
                .show();
    }

    /** Grava VRAM, CRAM, VSRAM, registradores do VDP, RAM e o quadro atual em Android/data/.../files/dumps. */
    private void dumpVideo() {
        File dir = new File(getExternalFilesDir("dumps"), String.valueOf(System.currentTimeMillis()));
        dir.mkdirs();
        renderer.runOnEmuThread(() -> toast(Native.dumpVideo(dir.getAbsolutePath())
                ? "Exportado em " + dir.getName() : "Falha ao exportar"));
        resume();
    }

    private void resume() {
        renderer.setPaused(false);
        hideSystemUi();
    }

    private void toast(String s) { runOnUiThread(() -> Toast.makeText(this, s, Toast.LENGTH_SHORT).show()); }

    @Override
    protected void onPause() {
        super.onPause();
        if (surface == null) return;
        renderer.setPaused(true);
        surface.queueEvent(() -> {
            Native.saveSram(sram.getAbsolutePath());
            Native.saveState(autoState.getAbsolutePath());
        });
        surface.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (surface == null) return;
        surface.onResume();
        renderer.setPaused(false);
        hideSystemUi();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (renderer == null) return;
        renderer.release();
        Native.saveSram(sram.getAbsolutePath());
        Native.unloadGame();
    }

    // Controle físico (Bluetooth/USB).
    private static int keyBit(int code) {
        switch (code) {
            case KeyEvent.KEYCODE_DPAD_UP: return Native.BTN_UP;
            case KeyEvent.KEYCODE_DPAD_DOWN: return Native.BTN_DOWN;
            case KeyEvent.KEYCODE_DPAD_LEFT: return Native.BTN_LEFT;
            case KeyEvent.KEYCODE_DPAD_RIGHT: return Native.BTN_RIGHT;
            case KeyEvent.KEYCODE_BUTTON_X: return Native.BTN_A;
            case KeyEvent.KEYCODE_BUTTON_A: return Native.BTN_B;
            case KeyEvent.KEYCODE_BUTTON_B: return Native.BTN_C;
            case KeyEvent.KEYCODE_BUTTON_START: return Native.BTN_START;
            default: return 0;
        }
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent e) {
        int bit = keyBit(e.getKeyCode());
        if (bit == 0 || controls == null) return super.dispatchKeyEvent(e);
        if (e.getAction() == KeyEvent.ACTION_DOWN) keyMask |= bit; else if (e.getAction() == KeyEvent.ACTION_UP) keyMask &= ~bit;
        controls.setHardwareMask(keyMask | axisMask);
        return true;
    }

    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent e) {
        if ((e.getSource() & InputDevice.SOURCE_JOYSTICK) == 0 || controls == null) return super.dispatchGenericMotionEvent(e);
        float x = e.getAxisValue(MotionEvent.AXIS_HAT_X) + e.getAxisValue(MotionEvent.AXIS_X);
        float y = e.getAxisValue(MotionEvent.AXIS_HAT_Y) + e.getAxisValue(MotionEvent.AXIS_Y);
        int m = 0;
        if (x < -0.5f) m |= Native.BTN_LEFT;
        if (x > 0.5f) m |= Native.BTN_RIGHT;
        if (y < -0.5f) m |= Native.BTN_UP;
        if (y > 0.5f) m |= Native.BTN_DOWN;
        axisMask = m;
        controls.setHardwareMask(keyMask | axisMask);
        return true;
    }
}
