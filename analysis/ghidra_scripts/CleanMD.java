// Desfaz código falso: o Mega Drive usa um 68000 puro, então instruções e modos de
// endereçamento do 68010/68020+ indicam dados desmontados por engano.
//@category PS4
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

public class CleanMD extends GhidraScript {
    private static final Set<String> NOT_68000 = Set.of(
            "rtm", "moves", "cas", "cas2", "chk2", "cmp2", "pack", "unpk", "callm", "bkpt", "rtd",
            "extb", "movec", "trapcc", "tbls", "tblu", "tblsn", "tblun", "lpstop", "divsl", "divul");

    @Override
    public void run() throws Exception {
        List<Address> bad = new ArrayList<>();
        for (Instruction ins : currentProgram.getListing().getInstructions(true)) {
            if (ins.getAddress().getOffset() >= 0x200000) break;
            if (isNot68000(ins)) bad.add(ins.getAddress());
        }

        int removedFns = 0, clearedRuns = 0;
        for (Address a : bad) {
            Instruction ins = getInstructionAt(a);
            if (ins == null) continue;
            Function f = getFunctionContaining(a);
            if (f != null && distanceInInstructions(f.getEntryPoint(), a) < 4) {
                // A própria função começa em dados.
                Address start = f.getEntryPoint(), end = f.getBody().getMaxAddress();
                removeFunction(f);
                clearListing(start, end);
                removedFns++;
                continue;
            }
            // Limpa a sequência sem referências de entrada que começa na instrução inválida.
            Address end = a;
            Instruction cur = ins;
            while (cur != null && (cur == ins || getReferencesTo(cur.getAddress()).length == 0)) {
                end = cur.getMaxAddress();
                if (cur.getFlowType().isTerminal()) break;
                cur = cur.getNext();
            }
            clearListing(a, end);
            createBookmark(a, "Cleanup", "Dados que estavam desmontados como código");
            if (f != null) CreateFunctionCmd.fixupFunctionBody(currentProgram, f, monitor);
            clearedRuns++;
        }
        println("Instruções não-68000: " + bad.size() + ", funções removidas: " + removedFns
                + ", trechos limpos: " + clearedRuns + ", funções restantes: "
                + currentProgram.getFunctionManager().getFunctionCount());
    }

    private static boolean isNot68000(Instruction ins) {
        String m = ins.getMnemonicString().toLowerCase();
        String base = m.contains(".") ? m.substring(0, m.indexOf('.')) : m;
        if (NOT_68000.contains(base) || base.startsWith("bf") || base.startsWith("trap") && !base.equals("trap") && !base.equals("trapv"))
            return true;
        // Multiplicação/divisão de 32 bits só existe a partir do 68020.
        if ((base.equals("mulu") || base.equals("muls") || base.equals("divu") || base.equals("divs")) && m.endsWith(".l"))
            return true;
        String text = ins.toString();
        // Índice com escala (*2, *4, *8) e endereçamento indireto em memória ([...]) são do 68020.
        return text.contains("*0x2") || text.contains("*0x4") || text.contains("*0x8") || text.contains("[");
    }

    private int distanceInInstructions(Address from, Address to) {
        int n = 0;
        Instruction i = getInstructionAt(from);
        while (i != null && i.getAddress().compareTo(to) < 0 && n < 10) {
            i = i.getNext();
            n++;
        }
        return n;
    }
}
