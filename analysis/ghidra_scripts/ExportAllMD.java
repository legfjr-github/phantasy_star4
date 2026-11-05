// Exporta a listagem de todas as funções (listing.asm) e o pseudocódigo de todas elas (decomp_all.c),
// para consulta por texto fora do Ghidra. ExportAllMD.java <pasta-de-saida> [so-listagem]
//@category PS4
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Symbol;

import java.io.File;
import java.io.PrintWriter;

public class ExportAllMD extends GhidraScript {
    @Override
    public void run() throws Exception {
        File out = new File(getScriptArgs()[0]);
        out.mkdirs();
        boolean listingOnly = getScriptArgs().length > 1;

        try (PrintWriter w = new PrintWriter(new File(out, "listing.asm"), "UTF-8")) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                w.println();
                w.println("; ==== " + f.getName() + " @ " + f.getEntryPoint());
                if (f.getComment() != null) w.println("; " + f.getComment().replace("\n", "\n; "));
                for (Instruction i : currentProgram.getListing().getInstructions(f.getBody(), true)) {
                    Symbol s = getSymbolAt(i.getAddress());
                    if (s != null && !s.getName().equals(f.getName())) w.println(s.getName() + ":");
                    String c = i.getComment(CodeUnit.PRE_COMMENT);
                    if (c != null) w.println("  ; " + c.replace("\n", "\n  ; "));
                    w.printf("  %s  %s%n", i.getAddress(), i);
                }
            }
        }
        if (listingOnly) return;

        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        int n = 0;
        try (PrintWriter w = new PrintWriter(new File(out, "decomp_all.c"), "UTF-8")) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                DecompileResults r = dec.decompileFunction(f, 30, monitor);
                w.println("// ==== " + f.getName() + " @ " + f.getEntryPoint());
                w.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// falha: " + r.getErrorMessage());
                if (++n % 250 == 0) println("decompiladas " + n);
            }
        }
        dec.dispose();
        println("total " + n);
    }
}
