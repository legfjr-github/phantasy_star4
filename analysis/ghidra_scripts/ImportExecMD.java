// Usa a cobertura real do emulador (export/exec_marks.bin: bit 1 = executado, bit 0 = lido como dado)
// para desmontar e criar funções onde o jogo de fato executou código, e listar instruções que o
// Ghidra tem como código mas que o jogo só leu como dado (candidatas a dado desmontado por engano).
//@category PS4
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

import java.io.File;
import java.io.PrintWriter;
import java.nio.file.Files;

public class ImportExecMD extends GhidraScript {
    @Override
    public void run() throws Exception {
        byte[] m = Files.readAllBytes(new File(getScriptArgs()[0]).toPath());
        int disasm = 0, created = 0, executed = 0, inFunc = 0;
        for (int a = 0x200; a < 0x200000; a++) {
            if ((m[a] & 2) == 0) continue;
            executed++;
            Address addr = toAddr(a);
            if (getInstructionAt(addr) == null) {
                if (getInstructionContaining(addr) != null) clearListing(getInstructionContaining(addr).getAddress());
                new DisassembleCommand(new AddressSet(addr), null, true).applyTo(currentProgram, monitor);
                if (getInstructionAt(addr) != null) disasm++;
            }
        }
        // Funções: cada execução fora de função vira uma, começando após o último rts/jmp/bra anterior.
        for (int a = 0x200; a < 0x200000; a++) {
            if ((m[a] & 2) == 0) continue;
            Address addr = toAddr(a);
            if (getFunctionContaining(addr) != null) { inFunc++; continue; }
            Instruction ins = getInstructionAt(addr);
            if (ins == null) continue;
            for (int i = 0; i < 400; i++) {
                Instruction prev = getInstructionBefore(ins.getAddress());
                if (prev == null) break;
                String mn = prev.getMnemonicString().toLowerCase();
                if (mn.startsWith("rts") || mn.startsWith("rte") || mn.startsWith("jmp") || mn.equals("bra")
                        || mn.startsWith("bra.") || prev.getMaxAddress().next() == null
                        || !prev.getMaxAddress().next().equals(ins.getAddress())) break;
                ins = prev;
            }
            Function f = createFunction(ins.getAddress(), null);
            if (f != null) created++;
        }
        // Código que o jogo só leu como dado: instruções sem nenhum byte executado e com bytes lidos.
        int suspicious = 0;
        try (PrintWriter w = new PrintWriter(new File(getScriptArgs()[1]), "UTF-8")) {
            w.println("instrucao,funcao,texto");
            for (Instruction i : currentProgram.getListing().getInstructions(toAddr(0x200), true)) {
                long a = i.getAddress().getOffset();
                if (a >= 0x200000) break;
                boolean read = false, exec = false;
                for (long b = a; b <= i.getMaxAddress().getOffset(); b++) {
                    read |= (m[(int) b] & 1) != 0;
                    exec |= (m[(int) b] & 2) != 0;
                }
                if (read && !exec) {
                    Function f = getFunctionContaining(i.getAddress());
                    w.printf("%s,%s,\"%s\"%n", i.getAddress(), f == null ? "" : f.getName(), i);
                    suspicious++;
                }
            }
        }
        println("executados: " + executed + ", desmontados agora: " + disasm + ", funcoes novas: " + created
                + ", ja em funcao: " + inFunc + ", instrucoes so lidas como dado: " + suspicious
                + ", total de funcoes: " + currentProgram.getFunctionManager().getFunctionCount());
    }
}
