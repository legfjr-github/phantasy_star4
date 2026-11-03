// Pontua funções candidatas a descompressor: operações de bit, leitura sequencial (An)+,
// laços dbf e chamadores que carregam um ponteiro da ROM logo antes de chamar.
//@category PS4
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.Reference;

import java.io.File;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

public class FindDecompMD extends GhidraScript {
    record Score(Function f, int bits, int reads, int loops, int size, int romCallers, int callers, double total) {}

    @Override
    public void run() throws Exception {
        List<Score> all = new ArrayList<>();
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            int bits = 0, reads = 0, loops = 0, size = 0;
            for (Instruction i : currentProgram.getListing().getInstructions(f.getBody(), true)) {
                size++;
                String m = i.getMnemonicString().toLowerCase();
                String t = i.toString();
                if (m.startsWith("lsr") || m.startsWith("lsl") || m.startsWith("roxl") || m.startsWith("roxr")
                        || m.startsWith("rol") || m.startsWith("ror") || m.startsWith("asl") || m.startsWith("btst")
                        || m.startsWith("addx") || (m.startsWith("add") && t.matches(".*D(\\d)\\w?,D\\1.*"))) bits++;
                if (t.contains(")+,")) reads++;
                if (m.startsWith("dbf") || m.startsWith("dbra")) loops++;
            }
            if (size < 12 || size > 400) continue;
            int callers = 0, romCallers = 0;
            for (Reference r : getReferencesTo(f.getEntryPoint())) {
                if (!r.getReferenceType().isCall()) continue;
                callers++;
                // Uma das 4 instruções antes da chamada carrega um endereço da ROM de dados (>= 0x80000).
                Instruction p = getInstructionAt(r.getFromAddress());
                for (int k = 0; k < 4 && p != null; k++) {
                    p = p.getPrevious();
                    if (p == null) break;
                    if (p.getMnemonicString().toLowerCase().startsWith("lea")) {
                        for (Object o : p.getOpObjects(0)) {
                            long v = o instanceof Scalar s ? s.getUnsignedValue() : o instanceof Address a ? a.getOffset() : -1;
                            if (v >= 0x80000 && v < 0x300000) { romCallers++; k = 9; break; }
                        }
                    }
                }
            }
            double total = (bits * 2.0 + reads + loops) / Math.sqrt(size) * Math.log(2 + romCallers);
            all.add(new Score(f, bits, reads, loops, size, romCallers, callers, total));
        }
        all.sort((a, b) -> Double.compare(b.total(), a.total()));
        try (PrintWriter w = new PrintWriter(new File(getScriptArgs()[0]), "UTF-8")) {
            w.println("entry,name,score,bit_ops,seq_reads,dbf,size,callers,callers_with_rom_ptr");
            for (Score s : all.subList(0, Math.min(40, all.size())))
                w.printf("%s,%s,%.2f,%d,%d,%d,%d,%d,%d%n", s.f().getEntryPoint(), s.f().getName(), s.total(),
                        s.bits(), s.reads(), s.loops(), s.size(), s.callers(), s.romCallers());
        }
    }
}
