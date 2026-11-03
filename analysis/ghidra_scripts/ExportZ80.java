// Driver de som Z80: marca o mapa de I/O do Mega Drive, cria funções a partir do reset e da
// interrupção (RST 38h) e exporta a listagem e o pseudocódigo.
//@category PS4
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.SourceType;

import java.io.File;
import java.io.PrintWriter;

public class ExportZ80 extends GhidraScript {
    @Override
    public void run() throws Exception {
        File out = new File(getScriptArgs()[0]);
        Memory mem = currentProgram.getMemory();
        mem.getBlock(toAddr(0)).setName("Z80_RAM");
        // A RAM do Z80 tem 8 KB; o driver ocupa o começo. Acima ficam YM2612, banco e PSG.
        mem.createUninitializedBlock("Z80_RAM_rest", toAddr(mem.getBlock(toAddr(0)).getSize()), 0x2000 - mem.getBlock(toAddr(0)).getSize(), false);
        mem.createUninitializedBlock("YM2612", toAddr(0x4000), 4, false).setVolatile(true);
        mem.createUninitializedBlock("BANK", toAddr(0x6000), 1, false).setVolatile(true);
        mem.createUninitializedBlock("PSG", toAddr(0x7F11), 1, false).setVolatile(true);
        mem.createUninitializedBlock("ROM_WINDOW", toAddr(0x8000), 0x8000, false);
        label(0x4000, "YM_ADDR0");
        label(0x4001, "YM_DATA0");
        label(0x4002, "YM_ADDR1");
        label(0x4003, "YM_DATA1");
        label(0x6000, "BANK_SELECT");
        label(0x7F11, "PSG_PORT");

        entry(0x0000, "Z80_Reset");
        entry(0x0038, "Z80_VBlank_RST38");
        analyzeChanges(currentProgram);

        try (PrintWriter w = new PrintWriter(new File(out, "z80_driver.asm"), "UTF-8")) {
            for (Instruction i : currentProgram.getListing().getInstructions(true)) {
                Function f = getFunctionAt(i.getAddress());
                if (f != null) w.println("\n; ---- " + f.getName());
                String lbl = getSymbolAt(i.getAddress()) == null ? "" : getSymbolAt(i.getAddress()).getName() + ":";
                w.printf("%-24s %s  %s%n", lbl, i.getAddress(), i);
            }
        }

        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        int fns = 0;
        try (PrintWriter w = new PrintWriter(new File(out, "z80_driver.c"), "UTF-8")) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                DecompileResults r = dec.decompileFunction(f, 60, monitor);
                w.println("// ==== " + f.getName() + " @ " + f.getEntryPoint());
                w.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// falha: " + r.getErrorMessage());
                fns++;
            }
        }
        dec.dispose();

        int ym = 0, psg = 0, bank = 0;
        for (long a : new long[]{0x4000, 0x4001, 0x4002, 0x4003}) ym += getReferencesTo(toAddr(a)).length;
        for (Reference r : getReferencesTo(toAddr(0x7F11))) psg++;
        for (Reference r : getReferencesTo(toAddr(0x6000))) bank++;
        println("Z80: " + fns + " funções, refs YM2612=" + ym + " PSG=" + psg + " banco=" + bank);
    }

    private void entry(long a, String name) throws Exception {
        Address addr = toAddr(a);
        addEntryPoint(addr);
        disassemble(addr);
        createFunction(addr, name);
    }

    private void label(long a, String name) throws Exception {
        createLabel(toAddr(a), name, true, SourceType.USER_DEFINED);
    }
}
