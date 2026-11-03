// Prepara uma ROM de Mega Drive: mapa de memória, vetores do 68000 e marcas dos códigos Game Genie.
//@category PS4
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.DWordDataType;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.SourceType;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;

public class SetupMD extends GhidraScript {
    private static final String[] VECTORS = {
        "SSP", "Reset", "BusError", "AddressError", "IllegalInstr", "ZeroDivide", "CHK", "TRAPV",
        "Privilege", "Trace", "Line1010", "Line1111"};

    @Override
    public void run() throws Exception {
        Memory mem = currentProgram.getMemory();
        MemoryBlock rom = mem.getBlock(toAddr(0));
        rom.setName("ROM");
        rom.setWrite(false);
        rom.setExecute(true);

        newBlock(mem, "Z80_RAM", 0xA00000, 0x2000);
        newBlock(mem, "IO", 0xA10000, 0x20);
        newBlock(mem, "Z80_CTRL", 0xA11000, 0x200);
        newBlock(mem, "VDP", 0xC00000, 0x20);
        newBlock(mem, "RAM", 0xFF0000, 0x10000);
        label(0xC00000, "VDP_DATA");
        label(0xC00004, "VDP_CTRL");
        label(0xA10001, "IO_VERSION");
        label(0xA10003, "IO_PAD1_DATA");
        label(0xA10009, "IO_PAD1_CTRL");
        label(0xA11100, "Z80_BUSREQ");
        label(0xA11200, "Z80_RESET");

        // Tabela de vetores: 64 ponteiros de 32 bits.
        for (int i = 0; i < 64; i++) {
            Address slot = toAddr(i * 4);
            createData(slot, new DWordDataType());
            long target = mem.getInt(slot) & 0xFFFFFFFFL;
            String name = i < VECTORS.length ? VECTORS[i]
                    : i == 28 ? "HBlank" : i == 30 ? "VBlank" : i == 26 ? "ExtInt" : null;
            if (i == 0 || target >= rom.getSize() || target == 0) continue;
            Address t = toAddr(target);
            if (name != null) label(target, name + "_Handler");
            addEntryPoint(t);
            disassemble(t);
            if (getFunctionAt(t) == null) createFunction(t, null);
        }

        // Endereços tocados pelos códigos Game Genie (CSV gerado antes).
        File csv = new File(getScriptArgs().length > 0 ? getScriptArgs()[0] : "gg_decoded.csv");
        if (csv.exists()) {
            try (BufferedReader r = new BufferedReader(new FileReader(csv))) {
                r.readLine();
                String line;
                while ((line = r.readLine()) != null) {
                    String[] f = line.replace("\"", "").split(",", 5);
                    Address a = toAddr(Long.parseLong(f[1], 16));
                    String old = currentProgram.getListing().getComment(CodeUnit.PRE_COMMENT, a);
                    String c = "GG " + f[0] + " (" + f[2] + " -> " + f[3] + "): " + f[4];
                    currentProgram.getListing().setComment(a, CodeUnit.PRE_COMMENT, old == null ? c : old + "\n" + c);
                    createBookmark(a, "GameGenie", f[4]);
                }
            }
        }
    }

    private void newBlock(Memory mem, String name, long start, long size) throws Exception {
        MemoryBlock b = mem.createUninitializedBlock(name, toAddr(start), size, false);
        b.setRead(true);
        b.setWrite(true);
        b.setVolatile(!name.equals("RAM"));
    }

    private void label(long addr, String name) throws Exception {
        createLabel(toAddr(addr), name, true, SourceType.USER_DEFINED);
    }
}
