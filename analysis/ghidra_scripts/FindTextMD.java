// Procura o interpretador de texto: funções que comparam bytes com vários códigos de controle
// (FC nova linha, FD nova página, FF fim, F4 retrato) ou usam o ponteiro FF4FD4.
//@category PS4
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.scalar.Scalar;

import java.util.Set;
import java.util.TreeSet;

public class FindTextMD extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            Set<Long> codes = new TreeSet<>();
            boolean ptr = false;
            for (Instruction i : currentProgram.getListing().getInstructions(f.getBody(), true)) {
                String m = i.getMnemonicString().toLowerCase();
                String t = i.toString().toLowerCase();
                if (t.contains("ff4fd4") || t.contains("-0x2c,a6") && t.contains("ff5000")) ptr = true;
                if (!m.startsWith("cmp")) continue;
                for (int op = 0; op < i.getNumOperands(); op++)
                    for (Object o : i.getOpObjects(op))
                        if (o instanceof Scalar s) {
                            long v = s.getValue() & 0xFF;
                            if (v >= 0xF0) codes.add(v);
                        }
            }
            if (codes.size() >= 3 || ptr) {
                StringBuilder sb = new StringBuilder();
                for (long c : codes) sb.append(String.format("%02X ", c));
                println(f.getEntryPoint() + " " + f.getName() + " codigos=" + sb + (ptr ? " usa FF4FD4" : ""));
            }
        }
    }
}
