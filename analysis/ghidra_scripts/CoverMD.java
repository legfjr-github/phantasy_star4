// Amplia a cobertura: segue jsr/jmp absolutos, bsr e tabelas de ponteiros para código,
// repetindo até não aparecerem funções novas.
//@category PS4
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;

import java.util.TreeSet;

public class CoverMD extends GhidraScript {
    private static final long CODE_END = 0x200000;

    @Override
    public void run() throws Exception {
        Memory mem = currentProgram.getMemory();
        byte[] rom = new byte[(int) CODE_END];
        mem.getBytes(toAddr(0), rom);

        int before = currentProgram.getFunctionManager().getFunctionCount();
        for (int pass = 1; pass <= 6; pass++) {
            TreeSet<Long> targets = new TreeSet<>();

            // 1) Alvos de jsr/jmp abs.l e bsr/bsr.w dentro de instruções já desmontadas.
            for (Instruction ins : currentProgram.getListing().getInstructions(true)) {
                if (ins.getAddress().getOffset() >= CODE_END) break;
                String m = ins.getMnemonicString().toLowerCase();
                if (!(m.startsWith("jsr") || m.startsWith("bsr") || m.startsWith("jmp"))) continue;
                for (Address f : ins.getFlows()) {
                    long t = f.getOffset();
                    if (t < CODE_END && (t & 1) == 0 && t >= 0x200) targets.add(t);
                }
            }

            // 2) Padrões soltos de jsr abs.l (4EB9 xxxxxxxx) em qualquer lugar da área de código.
            for (int i = 0x200; i + 6 <= rom.length; i += 2) {
                if ((rom[i] & 0xFF) == 0x4E && (rom[i + 1] & 0xFF) == 0xB9) {
                    long t = ((rom[i + 2] & 0xFFL) << 24) | ((rom[i + 3] & 0xFFL) << 16) | ((rom[i + 4] & 0xFFL) << 8) | (rom[i + 5] & 0xFFL);
                    if (t >= 0x200 && t < CODE_END && (t & 1) == 0 && looksLikeCode(rom, (int) t)) targets.add(t);
                }
            }

            // 3) Tabelas de ponteiros: 6+ longs seguidos, fora de instruções, todos apontando para código.
            for (int i = 0x200; i + 24 <= rom.length; i += 2) {
                int n = 0;
                while (i + n * 4 + 4 <= rom.length) {
                    long t = readLong(rom, i + n * 4);
                    if (t < 0x200 || t >= CODE_END || (t & 1) != 0 || !looksLikeCode(rom, (int) t)) break;
                    n++;
                }
                if (n < 6 || getInstructionContaining(toAddr(i)) != null) continue;
                for (int k = 0; k < n; k++) targets.add(readLong(rom, i + k * 4));
                if (pass == 1) createLabel(toAddr(i), String.format("PtrTable_%06X", i), false);
                i += n * 4 - 2;
            }

            int created = 0;
            for (long t : targets) {
                Address a = toAddr(t);
                if (getFunctionAt(a) != null) continue;
                if (getInstructionAt(a) == null) {
                    if (getDataContaining(a) != null) continue;
                    new DisassembleCommand(new AddressSet(a), null, true).applyTo(currentProgram, monitor);
                }
                if (getInstructionAt(a) == null) continue;
                Function f = createFunction(a, null);
                if (f != null) created++;
            }
            println("Passo " + pass + ": " + created + " funções novas");
            if (created == 0) break;
            analyzeChanges(currentProgram);
        }
        println("Funções: " + before + " -> " + currentProgram.getFunctionManager().getFunctionCount());
    }

    private static long readLong(byte[] rom, int i) {
        return ((rom[i] & 0xFFL) << 24) | ((rom[i + 1] & 0xFFL) << 16) | ((rom[i + 2] & 0xFFL) << 8) | (rom[i + 3] & 0xFFL);
    }

    /** Descarta alvos cujo primeiro opcode é zero ou 0xFFFF, comuns em áreas de dados. */
    private static boolean looksLikeCode(byte[] rom, int t) {
        int op = ((rom[t] & 0xFF) << 8) | (rom[t + 1] & 0xFF);
        return op != 0 && op != 0xFFFF;
    }
}
