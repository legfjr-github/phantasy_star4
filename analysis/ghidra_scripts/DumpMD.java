// Imprime 24 instruções a partir de cada endereço passado (hex), desmontando se preciso.
//@category PS4
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

public class DumpMD extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (String arg : getScriptArgs()) {
            Address a = toAddr(Long.parseLong(arg, 16));
            if (getInstructionContaining(a) == null) disassemble(a);
            Instruction ins = getInstructionContaining(a);
            if (ins == null) ins = getInstructionAfter(a);
            Function f = ins == null ? null : getFunctionContaining(ins.getAddress());
            println("==== " + a + " em " + (f == null ? "(sem função)" : f.getName() + " @ " + f.getEntryPoint()));
            // Começa no próprio endereço e segue o fluxo em sequência.
            for (int i = 0; i < 24 && ins != null; i++, ins = ins.getNext())
                println("  " + ins.getAddress() + "  " + ins);
        }
    }
}
