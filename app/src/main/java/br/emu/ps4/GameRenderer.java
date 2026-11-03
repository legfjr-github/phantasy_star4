package br.emu.ps4;

import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/** Roda o emulador no ritmo do jogo e desenha o quadro ampliado com o filtro escolhido. */
public class GameRenderer implements GLSurfaceView.Renderer {
    public static final int MODE_INTEGER = 0;
    public static final int MODE_SHARP = 1;
    public static final int MODE_CRT = 2;
    public static final int MODE_SMOOTH = 3;

    private static final String VERTEX =
            "attribute vec2 aPos; attribute vec2 aUv; varying vec2 vUv;\n" +
            "void main() { vUv = aUv; gl_Position = vec4(aPos, 0.0, 1.0); }";

    private static final String FRAG_PLAIN =
            "precision mediump float; varying vec2 vUv; uniform sampler2D uTex;\n" +
            "void main() { gl_FragColor = texture2D(uTex, vUv); }";

    // Sharp bilinear: pixels nítidos mesmo em escala não inteira.
    private static final String FRAG_SHARP =
            "precision highp float; varying vec2 vUv; uniform sampler2D uTex;\n" +
            "uniform vec2 uTexSize; uniform float uScale;\n" +
            "void main() {\n" +
            "  vec2 texel = vUv * uTexSize;\n" +
            "  float pre = max(floor(uScale), 1.0);\n" +
            "  float range = 0.5 - 0.5 / pre;\n" +
            "  vec2 d = fract(texel) - 0.5;\n" +
            "  vec2 f = (d - clamp(d, -range, range)) * pre + 0.5;\n" +
            "  gl_FragColor = texture2D(uTex, (floor(texel) + f) / uTexSize);\n" +
            "}";

    // Linhas de varredura simples, ao estilo de TV de tubo.
    private static final String FRAG_CRT =
            "precision highp float; varying vec2 vUv; uniform sampler2D uTex;\n" +
            "uniform vec2 uTexSize; uniform float uScale;\n" +
            "void main() {\n" +
            "  vec2 texel = vUv * uTexSize;\n" +
            "  vec2 uv = vec2((floor(texel.x) + 0.5) / uTexSize.x, vUv.y);\n" +
            "  vec3 c = texture2D(uTex, uv).rgb;\n" +
            "  float l = abs(fract(texel.y) - 0.5) * 2.0;\n" +
            "  float scan = 1.0 - 0.5 * l * l;\n" +
            "  gl_FragColor = vec4(c * scan * 1.15, 1.0);\n" +
            "}";

    private final ByteBuffer video = ByteBuffer.allocateDirect(720 * 576 * 2).order(ByteOrder.nativeOrder());
    private final short[] audio = new short[8192];
    private final FloatBuffer quad = ByteBuffer.allocateDirect(16 * 4).order(ByteOrder.nativeOrder()).asFloatBuffer();

    private final int mode;
    private final boolean stretch;
    private AudioTrack track;
    private int program, tex, texW, texH;
    private int viewW, viewH;
    private long lastNs;
    private double accNs;
    private volatile boolean paused;
    private volatile Runnable pending;
    private volatile int speed = 1;
    private long frameCount;

    public GameRenderer(int mode, boolean stretch) {
        this.mode = mode;
        this.stretch = stretch;
    }

    public void setPaused(boolean p) {
        paused = p;
        lastNs = 0;
        if (track != null) {
            if (p) track.pause(); else track.play();
        }
    }

    /** Multiplicador de velocidade: 1 a 4. */
    public void setSpeed(int s) { speed = s; }

    /** Executa uma ação na thread do emulador, entre dois quadros. */
    public void runOnEmuThread(Runnable r) { pending = r; }

    @Override
    public void onSurfaceCreated(GL10 gl, EGLConfig config) {
        String frag = mode == MODE_SHARP ? FRAG_SHARP : mode == MODE_CRT ? FRAG_CRT : FRAG_PLAIN;
        program = link(VERTEX, frag);
        int[] t = new int[1];
        GLES20.glGenTextures(1, t, 0);
        tex = t[0];
        int filter = mode == MODE_INTEGER ? GLES20.GL_NEAREST : GLES20.GL_LINEAR;
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, tex);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, filter);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, filter);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE);
        texW = texH = 0;

        if (track == null) {
            int rate = Native.sampleRate();
            int min = AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_STEREO, AudioFormat.ENCODING_PCM_16BIT);
            track = new AudioTrack(AudioManager.STREAM_MUSIC, rate, AudioFormat.CHANNEL_OUT_STEREO,
                    AudioFormat.ENCODING_PCM_16BIT, Math.max(min * 2, rate / 5 * 4), AudioTrack.MODE_STREAM);
            track.play();
        }
    }

    @Override
    public void onSurfaceChanged(GL10 gl, int w, int h) {
        viewW = w;
        viewH = h;
    }

    @Override
    public void onDrawFrame(GL10 gl) {
        Runnable r = pending;
        if (r != null) {
            pending = null;
            r.run();
        }
        if (!paused) step();
        draw();
    }

    private void step() {
        long now = System.nanoTime();
        if (lastNs == 0) lastNs = now - (long) (1e9 / Native.fps());
        accNs += now - lastNs;
        lastNs = now;
        int s = speed;
        double frameNs = 1e9 / (Native.fps() * s);
        int runs = 0;
        while (accNs >= frameNs && runs < 3 * s) {
            int n = Native.runFrame(video, audio);
            // Acelerado, só um quadro em cada `s` vai para o áudio, para o som não atrasar.
            if (frameCount++ % s == 0) track.write(audio, 0, n, AudioTrack.WRITE_NON_BLOCKING);
            accNs -= frameNs;
            runs++;
        }
        if (accNs > frameNs * 3 * s) accNs = 0;
    }

    private void draw() {
        int fw = Native.frameWidth(), fh = Native.frameHeight();
        GLES20.glViewport(0, 0, viewW, viewH);
        GLES20.glClearColor(0, 0, 0, 1);
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT);

        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, tex);
        video.position(0);
        if (fw != texW || fh != texH) {
            GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGB, fw, fh, 0,
                    GLES20.GL_RGB, GLES20.GL_UNSIGNED_SHORT_5_6_5, video);
            texW = fw;
            texH = fh;
        } else {
            GLES20.glTexSubImage2D(GLES20.GL_TEXTURE_2D, 0, 0, 0, fw, fh,
                    GLES20.GL_RGB, GLES20.GL_UNSIGNED_SHORT_5_6_5, video);
        }

        // Área de saída: 4:3 na altura total, inteira no modo nítido, ou esticada.
        float outH, outW;
        if (stretch) {
            outW = viewW;
            outH = viewH;
        } else {
            outH = mode == MODE_INTEGER ? fh * Math.max(1, viewH / fh) : viewH;
            outW = outH * 4f / 3f;
            if (outW > viewW) {
                outW = viewW;
                outH = outW * 3f / 4f;
            }
        }
        float x = outW / viewW, y = outH / viewH;
        quad.position(0);
        quad.put(new float[]{-x, -y, 0, 1, x, -y, 1, 1, -x, y, 0, 0, x, y, 1, 0});

        GLES20.glUseProgram(program);
        int aPos = GLES20.glGetAttribLocation(program, "aPos");
        int aUv = GLES20.glGetAttribLocation(program, "aUv");
        quad.position(0);
        GLES20.glVertexAttribPointer(aPos, 2, GLES20.GL_FLOAT, false, 16, quad);
        quad.position(2);
        GLES20.glVertexAttribPointer(aUv, 2, GLES20.GL_FLOAT, false, 16, quad);
        GLES20.glEnableVertexAttribArray(aPos);
        GLES20.glEnableVertexAttribArray(aUv);
        GLES20.glUniform2f(GLES20.glGetUniformLocation(program, "uTexSize"), fw, fh);
        GLES20.glUniform1f(GLES20.glGetUniformLocation(program, "uScale"), outH / fh);
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4);
    }

    public void release() {
        if (track != null) {
            track.release();
            track = null;
        }
    }

    private static int link(String vs, String fs) {
        int p = GLES20.glCreateProgram();
        GLES20.glAttachShader(p, compile(GLES20.GL_VERTEX_SHADER, vs));
        GLES20.glAttachShader(p, compile(GLES20.GL_FRAGMENT_SHADER, fs));
        GLES20.glLinkProgram(p);
        return p;
    }

    private static int compile(int type, String src) {
        int s = GLES20.glCreateShader(type);
        GLES20.glShaderSource(s, src);
        GLES20.glCompileShader(s);
        return s;
    }
}
