// Para cada função passada (hex), lista as chamadas e o endereço que cada uma carrega em A0
// (lea abs ou movea.l #abs) nas instruções anteriores.
//@category PS4
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.Reference;

import java.io.File;
import java.io.PrintWriter;

public class CallArgsMD extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        try (PrintWriter w = new PrintWriter(new File(args[0]), "UTF-8")) {
            w.println("callee,call_site,caller,a0");
            for (int n = 1; n < args.length; n++) {
                Address callee = toAddr(Long.parseLong(args[n], 16));
                for (Reference r : getReferencesTo(callee)) {
                    if (!r.getReferenceType().isCall() && !r.getReferenceType().isJump()) continue;
                    Instruction p = getInstructionAt(r.getFromAddress());
                    String a0 = "";
                    for (int k = 0; k < 8 && p != null && a0.isEmpty(); k++) {
                        p = p.getPrevious();
                        if (p == null) break;
                        String m = p.getMnemonicString().toLowerCase();
                        if (!(m.startsWith("lea") || m.startsWith("movea")) || !p.toString().endsWith(",A0")) continue;
                        for (Object o : p.getOpObjects(0)) {
                            long v = o instanceof Scalar s ? s.getUnsignedValue() : o instanceof Address a ? a.getOffset() : -1;
                            if (v >= 0) a0 = String.format("%06X", v);
                        }
                        // lea (d,PC),A0: o Ghidra já resolve como endereço.
                        if (a0.isEmpty() && p.getOperandReferences(0).length > 0)
                            a0 = String.format("%06X", p.getOperandReferences(0)[0].getToAddress().getOffset());
                        if (a0.isEmpty()) a0 = "?" + p;
                    }
                    Function f = getFunctionContaining(r.getFromAddress());
                    w.printf("%s,%s,%s,%s%n", callee, r.getFromAddress(), f == null ? "" : f.getName(), a0);
                }
            }
        }
    }
}
