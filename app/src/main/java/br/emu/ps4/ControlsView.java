package br.emu.ps4;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.view.MotionEvent;
import android.view.View;

/** Controle virtual multitoque: direcional, A/B/C, Start e botão de menu. */
public class ControlsView extends View {
    public interface Listener {
        void onInput(int mask);
        void onMenu();
        void onSpeed(int speed);
    }

    private static final String[] LABELS = {"A", "B", "C"};
    private static final int[] BITS = {Native.BTN_A, Native.BTN_B, Native.BTN_C};

    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Listener listener;
    private float padX, padY, padR, btnR, startX, startY, menuX, menuY, speedX, speedY;
    private int speed = 1;
    private final float[] btnX = new float[3], btnY = new float[3];
    private int mask;
    private int hardwareMask;

    public ControlsView(Context c, Listener l) {
        super(c);
        listener = l;
        text.setColor(Color.argb(200, 255, 255, 255));
        text.setTextAlign(Paint.Align.CENTER);
        text.setFakeBoldText(true);
    }

    /** Estado vindo de um controle físico, somado ao toque. */
    public void setHardwareMask(int m) {
        hardwareMask = m;
        listener.onInput(mask | hardwareMask);
    }

    @Override
    protected void onSizeChanged(int w, int h, int ow, int oh) {
        float u = Math.min(w, h);
        padR = u * 0.2f;
        padX = padR * 1.25f;
        padY = h - padR * 1.25f;
        btnR = u * 0.075f;
        // A/B/C em diagonal dentro da faixa lateral, para não cobrir a imagem 4:3.
        // Passo de 1,6r x 1,5r deixa ~0,2r de folga entre os círculos.
        float side = Math.max((w - h * 4f / 3f) / 2f, btnR * 5.4f);
        float cx = w - side / 2f, by = h - u * 0.3f;
        btnX[0] = cx - btnR * 1.6f; btnY[0] = by + btnR * 1.5f;
        btnX[1] = cx;               btnY[1] = by;
        btnX[2] = cx + btnR * 1.6f; btnY[2] = by - btnR * 1.5f;
        speedX = btnR * 1.2f;
        speedY = btnR * 1.2f;
        startX = cx;
        startY = by - btnR * 3.8f;
        menuX = w - btnR * 1.2f;
        menuY = btnR * 1.2f;
        text.setTextSize(btnR * 0.8f);
    }

    @Override
    protected void onDraw(Canvas c) {
        fill.setColor(Color.argb(60, 255, 255, 255));
        c.drawCircle(padX, padY, padR, fill);
        fill.setColor(Color.argb(90, 255, 255, 255));
        c.drawCircle(padX, padY, padR * 0.35f, fill);
        for (int i = 0; i < 3; i++) {
            fill.setColor((mask & BITS[i]) != 0 ? Color.argb(140, 255, 255, 255) : Color.argb(70, 255, 255, 255));
            c.drawCircle(btnX[i], btnY[i], btnR, fill);
            c.drawText(LABELS[i], btnX[i], btnY[i] + btnR * 0.3f, text);
        }
        fill.setColor(Color.argb(70, 255, 255, 255));
        c.drawRoundRect(startX - btnR * 1.3f, startY - btnR * 0.45f, startX + btnR * 1.3f, startY + btnR * 0.45f,
                btnR * 0.45f, btnR * 0.45f, fill);
        text.setTextSize(btnR * 0.45f);
        c.drawText("START", startX, startY + btnR * 0.16f, text);
        c.drawCircle(menuX, menuY, btnR * 0.7f, fill);
        c.drawText("≡", menuX, menuY + btnR * 0.16f, text);
        fill.setColor(speed > 1 ? Color.argb(150, 255, 200, 60) : Color.argb(70, 255, 255, 255));
        c.drawCircle(speedX, speedY, btnR * 0.7f, fill);
        c.drawText(speed + "x", speedX, speedY + btnR * 0.16f, text);
        text.setTextSize(btnR * 0.8f);
    }

    @Override
    public boolean onTouchEvent(MotionEvent e) {
        int action = e.getActionMasked();
        if (action == MotionEvent.ACTION_DOWN || action == MotionEvent.ACTION_POINTER_DOWN) {
            int i = e.getActionIndex();
            if (dist(e.getX(i), e.getY(i), menuX, menuY) < btnR) {
                listener.onMenu();
                return true;
            }
            if (dist(e.getX(i), e.getY(i), speedX, speedY) < btnR) {
                speed = speed % 4 + 1;
                listener.onSpeed(speed);
                invalidate();
                return true;
            }
        }
        int m = 0;
        for (int i = 0; i < e.getPointerCount(); i++) {
            boolean up = (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_POINTER_UP)
                    && i == e.getActionIndex();
            if (action == MotionEvent.ACTION_CANCEL || up) continue;
            m |= hit(e.getX(i), e.getY(i));
        }
        if (m != mask) {
            mask = m;
            listener.onInput(mask | hardwareMask);
            invalidate();
        }
        return true;
    }

    private int hit(float x, float y) {
        float dx = x - padX, dy = y - padY;
        float d = (float) Math.hypot(dx, dy);
        if (d < padR * 1.4f && d > padR * 0.2f) {
            // Oito direções em setores de 45 graus.
            double a = Math.toDegrees(Math.atan2(-dy, dx));
            if (a < 0) a += 360;
            int m = 0;
            if (a < 67.5 || a > 292.5) m |= Native.BTN_RIGHT;
            if (a > 22.5 && a < 157.5) m |= Native.BTN_UP;
            if (a > 112.5 && a < 247.5) m |= Native.BTN_LEFT;
            if (a > 202.5 && a < 337.5) m |= Native.BTN_DOWN;
            return m;
        }
        for (int i = 0; i < 3; i++)
            if (dist(x, y, btnX[i], btnY[i]) < btnR * 1.15f) return BITS[i];
        if (Math.abs(x - startX) < btnR * 1.5f && Math.abs(y - startY) < btnR * 0.8f) return Native.BTN_START;
        return 0;
    }

    private static float dist(float x1, float y1, float x2, float y2) {
        return (float) Math.hypot(x1 - x2, y1 - y2);
    }
}
