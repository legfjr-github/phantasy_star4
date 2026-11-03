// Exporta a lista de funções e o pseudocódigo das funções que contêm endereços dos códigos Game Genie.
//@category PS4
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Bookmark;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

import ghidra.program.model.listing.CodeUnit;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;
import java.io.PrintWriter;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

public class ExportMD extends GhidraScript {
    @Override
    public void run() throws Exception {
        File out = new File(getScriptArgs()[0]);
        out.mkdirs();

        try (PrintWriter w = new PrintWriter(new File(out, "functions.csv"), "UTF-8")) {
            w.println("entry,name,size,callers,callees");
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                int callers = 0;
                for (Reference r : getReferencesTo(f.getEntryPoint()))
                    if (r.getReferenceType().isCall()) callers++;
                w.printf("%s,%s,%d,%d,%d%n", f.getEntryPoint(), f.getName(), f.getBody().getNumAddresses(),
                        callers, f.getCalledFunctions(monitor).size());
            }
        }

        // Funções de código que contêm um patch Game Genie (os patches em tabelas de dados ficam de fora).
        Map<Function, StringBuilder> hits = new LinkedHashMap<>();
        StringBuilder loose = new StringBuilder();
        int marks = 0;
        List<String[]> rows = new ArrayList<>();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(new FileInputStream(getScriptArgs()[1]), "UTF-8"))) {
            r.readLine();
            String line;
            while ((line = r.readLine()) != null) rows.add(line.replace("\"", "").split(",", 5));
        }
        java.util.Set<Address> fresh = new java.util.HashSet<>();
        for (String[] row : rows) {
            marks++;
            Address a = toAddr(Long.parseLong(row[1], 16));
            String note = "GG " + row[0] + " (" + row[2] + " -> " + row[3] + "): " + row[4];
            // Recria o comentário a cada execução, a partir do CSV.
            String old = fresh.add(a) ? null : currentProgram.getListing().getComment(CodeUnit.PRE_COMMENT, a);
            currentProgram.getListing().setComment(a, CodeUnit.PRE_COMMENT, old == null ? note : old + "\n" + note);
            createBookmark(a, "GameGenie", row[4]);
            // Abaixo de 0x200000 é código; acima ficam as tabelas de itens/técnicas.
            if (a.getOffset() >= 0x200000) continue;
            if (getInstructionAt(a) == null) disassemble(a);
            Function f = getFunctionContaining(a);
            if (f == null) f = createFunctionAround(a);
            if (f == null) {
                loose.append("// ==== ").append(a).append(": ").append(note).append('\n');
                Instruction ins = getInstructionAt(a);
                for (int i = 0; i < 12 && ins != null && ins.getPrevious() != null; i++) ins = ins.getPrevious();
                for (int i = 0; i < 30 && ins != null; i++, ins = ins.getNext())
                    loose.append(ins.getAddress().equals(a) ? "=> " : "   ").append(ins.getAddress())
                            .append("  ").append(ins).append('\n');
                loose.append('\n');
                continue;
            }
            if (f != null) hits.computeIfAbsent(f, k -> new StringBuilder())
                    .append("//   ").append(a).append(": ").append(note).append('\n');
        }

        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        try (PrintWriter w = new PrintWriter(new File(out, "gg_functions.c"), "UTF-8")) {
            for (Map.Entry<Function, StringBuilder> e : hits.entrySet()) {
                Function f = e.getKey();
                DecompileResults r = dec.decompileFunction(f, 60, monitor);
                w.println("// ==== " + f.getName() + " @ " + f.getEntryPoint());
                w.print(e.getValue());
                w.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// falha: " + r.getErrorMessage());
                w.println();
            }
        }
        dec.dispose();
        try (PrintWriter w = new PrintWriter(new File(out, "gg_loose.asm"), "UTF-8")) {
            w.print(loose);
        }
        println("Funcoes: " + currentProgram.getFunctionManager().getFunctionCount() + ", marcas GG: " + marks
                + ", funcoes com patch: " + hits.size());
    }

    /** Procura para trás o início provável da rotina (depois de um RTS/RTE/JMP) e cria a função ali. */
    private Function createFunctionAround(Address a) {
        Instruction ins = getInstructionAt(a);
        for (int i = 0; i < 400 && ins != null; i++) {
            Instruction prev = getInstructionBefore(ins.getAddress());
            if (prev == null) break;
            String m = prev.getMnemonicString().toLowerCase();
            if (m.startsWith("rts") || m.startsWith("rte") || m.startsWith("jmp") || m.equals("bra") || m.startsWith("bra.")) break;
            ins = prev;
        }
        if (ins == null) return null;
        Function f = createFunction(ins.getAddress(), null);
        return f != null && f.getBody().contains(a) ? f : getFunctionContaining(a);
    }
}
