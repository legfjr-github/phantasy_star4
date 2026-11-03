// Grava o pseudocódigo das funções passadas (hex) num arquivo: DecompMD.java <saida.c> <end>...
//@category PS4
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;

import java.io.File;
import java.io.PrintWriter;

public class DecompMD extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        try (PrintWriter w = new PrintWriter(new File(args[0]), "UTF-8")) {
            for (int i = 1; i < args.length; i++) {
                Function f = getFunctionContaining(toAddr(Long.parseLong(args[i], 16)));
                if (f == null) { w.println("// sem função em " + args[i]); continue; }
                DecompileResults r = dec.decompileFunction(f, 60, monitor);
                w.println("// ==== " + f.getName() + " @ " + f.getEntryPoint());
                w.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// falha: " + r.getErrorMessage());
            }
        }
        dec.dispose();
    }
}
