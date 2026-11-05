package br.emu.ps4;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

/** Tela inicial: escolher a ROM, o filtro de imagem e os códigos de trapaça. */
public class MainActivity extends Activity {
    static final String PREFS = "config";
    static final String ROM_NAME = "rom.bin";
    /** Estado salvo sozinho ao sair da tela do jogo, separado dos 5 slots. */
    static final String AUTO_STATE = "auto.sav";
    private static final int PICK_ROM = 1;

    private SharedPreferences prefs;
    private TextView romStatus;
    private Spinner video;
    private CheckBox stretch, resume;
    private EditText cheats;
    private final CheckBox[] cheatBoxes = new CheckBox[Cheats.ALL.length];

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Phantasy Star IV Mobile");
        title.setTextSize(22);
        col.addView(title);

        romStatus = new TextView(this);
        col.addView(romStatus);
        Button pick = new Button(this);
        pick.setText("Escolher ROM");
        pick.setOnClickListener(v -> {
            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            i.addCategory(Intent.CATEGORY_OPENABLE);
            i.setType("*/*");
            startActivityForResult(i, PICK_ROM);
        });
        col.addView(pick);

        col.addView(label("Imagem (upscale)"));
        video = new Spinner(this);
        video.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item,
                new String[]{"Pixel nítido (escala inteira)", "Pixel nítido (tela cheia)", "CRT (linhas de TV)", "Suave (bilinear)"}));
        video.setSelection(prefs.getInt("video", GameRenderer.MODE_SHARP));
        col.addView(video);
        stretch = new CheckBox(this);
        stretch.setText("Esticar para preencher a tela");
        stretch.setChecked(prefs.getBoolean("stretch", false));
        col.addView(stretch);
        resume = new CheckBox(this);
        resume.setText("Continuar de onde parei (salva ao sair)");
        resume.setChecked(prefs.getBoolean("resume", true));
        col.addView(resume);

        col.addView(label("Modificadores"));
        LinearLayout section = null;
        String category = null;
        for (int i = 0; i < Cheats.ALL.length; i++) {
            Cheats.Cheat ch = Cheats.ALL[i];
            if (!ch.category.equals(category)) {
                // Cabeçalho que abre/fecha a categoria.
                category = ch.category;
                LinearLayout body = new LinearLayout(this);
                body.setOrientation(LinearLayout.VERTICAL);
                body.setVisibility(android.view.View.GONE);
                TextView head = new TextView(this);
                String catName = category;
                head.setText("▸ " + catName);
                head.setTextSize(17);
                head.setPadding(0, pad / 2, 0, pad / 2);
                head.setOnClickListener(v -> {
                    boolean open = body.getVisibility() != android.view.View.VISIBLE;
                    body.setVisibility(open ? android.view.View.VISIBLE : android.view.View.GONE);
                    head.setText((open ? "▾ " : "▸ ") + catName);
                });
                col.addView(head);
                col.addView(body);
                section = body;
            }
            CheckBox box = new CheckBox(this);
            box.setText(ch.name + "  [" + ch.code + "]");
            box.setChecked(prefs.getBoolean(ch.key(), false));
            box.setOnCheckedChangeListener((v, on) -> {
                if (!on || ch.group == null) return;
                for (int j = 0; j < Cheats.ALL.length; j++)
                    if (cheatBoxes[j] != v && ch.group.equals(Cheats.ALL[j].group)) cheatBoxes[j].setChecked(false);
            });
            cheatBoxes[i] = box;
            section.addView(box);
        }

        col.addView(label("Códigos extras Game Genie / Action Replay (um por linha, # comenta)"));
        cheats = new EditText(this);
        cheats.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE
                | InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        cheats.setMinLines(4);
        cheats.setGravity(Gravity.TOP);
        cheats.setHint("ABCD-EFGH\nFF0000:0063");
        cheats.setText(prefs.getString("cheats", ""));
        col.addView(cheats);

        Button play = new Button(this);
        play.setText("Jogar");
        play.setOnClickListener(v -> {
            if (!romFile().exists()) {
                Toast.makeText(this, "Escolha a ROM primeiro", Toast.LENGTH_SHORT).show();
                return;
            }
            save();
            startActivity(new Intent(this, GameActivity.class));
        });
        col.addView(play);

        ScrollView scroll = new ScrollView(this);
        scroll.setFitsSystemWindows(true);
        scroll.addView(col);
        setContentView(scroll);
        updateStatus();
    }

    private TextView label(String s) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setPadding(0, (int) (16 * getResources().getDisplayMetrics().density), 0, 0);
        return t;
    }

    private File romFile() { return new File(getFilesDir(), ROM_NAME); }

    private void updateStatus() {
        File f = romFile();
        romStatus.setText(f.exists() ? "ROM carregada (" + f.length() / 1024 + " KB)" : "Nenhuma ROM escolhida");
    }

    private void save() {
        SharedPreferences.Editor e = prefs.edit();
        for (int i = 0; i < Cheats.ALL.length; i++)
            e.putBoolean(Cheats.ALL[i].key(), cheatBoxes[i].isChecked());
        e.putInt("video", video.getSelectedItemPosition())
                .putBoolean("stretch", stretch.isChecked())
                .putBoolean("resume", resume.isChecked())
                .putString("cheats", cheats.getText().toString())
                .apply();
    }

    @Override
    protected void onPause() {
        super.onPause();
        save();
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (req != PICK_ROM || res != RESULT_OK || data == null) return;
        Uri uri = data.getData();
        try (InputStream in = getContentResolver().openInputStream(uri);
             OutputStream out = new FileOutputStream(romFile())) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            // O estado automático é da ROM anterior.
            new File(getFilesDir(), AUTO_STATE).delete();
        } catch (Exception e) {
            Toast.makeText(this, "Erro ao copiar a ROM: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
        updateStatus();
    }
}
