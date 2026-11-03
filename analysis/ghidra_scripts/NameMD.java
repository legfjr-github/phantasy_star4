// Aplica os nomes deduzidos da análise dos códigos Game Genie.
//@category PS4
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.ArrayDataType;
import ghidra.program.model.data.ByteDataType;
import ghidra.program.model.data.CategoryPath;
import ghidra.program.model.data.DWordDataType;
import ghidra.program.model.data.StructureDataType;
import ghidra.program.model.data.WordDataType;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

public class NameMD extends GhidraScript {
    @Override
    public void run() throws Exception {
        // Funções
        fn(0x303A, "Battle_GiveRewards", "Divide o XP total pelo número de membros vivos (divu D2,D1) e soma em cada personagem;\n"
                + "depois soma a recompensa de meseta (FF41D0) ao meseta do grupo. Limite de 9.999.999 em ambos.");
        fn(0x3152, "Battle_RollItemDrop", "Sorteia o item deixado pelo inimigo; contador em FF4190.");
        fn(0x9178, "Battle_SpendTechniqueTP", "Subtrai o custo de TP (tabela 2A9BE0 + id*8 + 1) do personagem em batalha.");
        fn(0x6112A, "Field_SpendTechniqueTP", "Subtrai TP (D0) de Char[D1].tp fora de batalha.");
        fn(0x659EE, "Shop_ChargeMeseta", "Desconta D0 do meseta do grupo após uma compra.");
        fn(0x65352, "Shop_BuyItem", "Compra: verifica se há meseta suficiente, entrega o item e desconta o preço.");
        fn(0x58B7A, "Field_OpenChest", "Abre um baú do mapa.");
        fn(0x66C72, "Field_ChestMesetaReward", null);
        fn(0x44414, "NewGame_Init", "Zera o estado, copia os personagens iniciais de 2A8DA0 e define meseta = 500.");
        fn(0x41682, "WaitVBlank", "Espera um quadro.");
        fn(0x41BEA, "KosinskiDec", "Descompressor Kosinski: A0 = origem, A1 = destino.");
        fn(0x41A90, "EnigmaDec", "Descompressor Enigma (mapas de tiles): A0 = origem, A1 = destino, D0 = base somada às palavras de cópia.");
        fn(0x41752, "NemesisDec", "Descompressor Nemesis para RAM: A0 = origem, A4 = destino. Buffer de código em FFE200.");
        fn(0x41740, "NemesisDecToVDP", "Descompressor Nemesis direto para VDP_DATA (endereço já definido em VDP_CTRL).");
        fn(0xD0C1A, "Sound_LoadZ80Driver", "Para o Z80, copia 0x522 bytes de 0xD153E para a RAM do Z80 e o reinicia.\n"
                + "O Z80 só toca samples PCM pelo DAC; a música FM é tocada pelo 68000 (RAM em FF5000).");
        tbl(0xD153E, "Z80_DriverBlob", "Driver Z80 (0x522 bytes). Ver analysis/z80.");
        tbl(0x0E0000, "PCM_SampleBanks", "Samples PCM 8 bits do DAC, 4 bancos de 32 KB (0x0E0000-0x0FFFFF).");
        tbl(0x2A303A, "Font_Nemesis", "Fonte principal (maiúsculas e dígitos), Nemesis.");
        tbl(0x280D08, "Names_ClassesAndMonsters", "Listas de nomes: 0x01-0x1A = A-Z, FE/FF terminam.");
        tbl(0x2AAFB4, "Names_Items", "Lista de 200 nomes de itens.");
        fn(0x6A090, "Text_Interpreter", "Desenha uma mensagem a partir de A0. Bytes < F0 são caracteres; F0-FF são\n"
                + "controles pelo nibble baixo (F2 sub-rotina via tabela 0x6A550, F4 retrato, F5 pergunta,\n"
                + "F9 pausa, FA condição, FC nova linha, FD nova página, F7/FF fim).");
        tbl(0x1DF5CA, "Dialogue_KosinskiBlocks", "43 blocos de diálogo comprimidos em Kosinski (até 0x1FE650).\n"
                + "O jogo descomprime o bloco da área atual para a RAM em FF3000.");
        tbl(0x1FE650, "Dialogue_PlainExamine", "Mensagens sem compressão ('não tem nada aqui').");
        lbl(0xFFFF3000L, "Dialogue_Buffer", new ArrayDataType(new ByteDataType(), 0x2000, 1));

        // RAM: o 68000 usa 24 bits, e o jogo acessa a RAM com endereços curtos (0xFFFFxxxx).
        if (currentProgram.getMemory().getBlock(toAddr(0xFFFF0000L)) == null)
            currentProgram.getMemory().createByteMappedBlock("RAM_MIRROR", toAddr(0xFFFF0000L), toAddr(0xFF0000), 0x10000, false);
        lbl(0xFFFFF438L, "Party_Meseta", new DWordDataType());
        lbl(0xFFFFF40AL, "Party_Members", new ArrayDataType(new ByteDataType(), 6, 1));
        lbl(0xFFFF41D0L, "Battle_MesetaReward", new WordDataType());
        lbl(0xFFFF4190L, "Battle_ItemDropCounter", new WordDataType());
        lbl(0xFFFFEF03L, "Pad1_Pressed", new ByteDataType());

        StructureDataType ch = new StructureDataType(new CategoryPath("/PS4"), "Character", 0x80);
        ch.replaceAtOffset(0x0A, new DWordDataType(), 4, "xp", "experiência acumulada");
        ch.replaceAtOffset(0x12, new WordDataType(), 2, "tp", "TP atual");
        ch.replaceAtOffset(0x16, new ByteDataType(), 1, "status", "0x44 = morto/fora do grupo");
        ch.replaceAtOffset(0x7A, new ByteDataType(), 1, "level_up_flag", null);
        Address chars = toAddr(0xFFFFF500L);
        clearListing(chars, chars.add(11 * 0x80 - 1));
        createData(chars, new ArrayDataType(currentProgram.getDataTypeManager().addDataType(ch, null), 11, 0x80));
        createLabel(chars, "Characters", true, SourceType.USER_DEFINED);

        // ROM: tabelas
        tbl(0x2A9BE0, "Table_Techniques", "Técnicas, 8 bytes cada; +1 = custo de TP, +2/+3 = alvo/potência.");
        tbl(0x2A98C0, "Table_ItemEffects", "Efeitos de itens (Monomate em 2A98D0, Dimate em 2A98E8).");
        tbl(0x2A8ACE, "Table_ChazStart", "Nível, equipamento e atributos iniciais do Chaz.");
        tbl(0x2A8DA0, "Table_StartingParty", "Personagens iniciais copiados por NewGame_Init.");
    }

    private void fn(long a, String name, String comment) throws Exception {
        Address addr = toAddr(a);
        Function f = getFunctionAt(addr);
        if (f == null) f = createFunction(addr, name);
        if (f == null) return;
        f.setName(name, SourceType.USER_DEFINED);
        if (comment != null) f.setComment(comment);
    }

    private void lbl(long a, String name, ghidra.program.model.data.DataType t) throws Exception {
        Address addr = toAddr(a);
        clearListing(addr, addr.add(t.getLength() - 1));
        createData(addr, t);
        createLabel(addr, name, true, SourceType.USER_DEFINED);
    }

    private void tbl(long a, String name, String comment) throws Exception {
        Address addr = toAddr(a);
        createLabel(addr, name, true, SourceType.USER_DEFINED);
        currentProgram.getListing().setComment(addr, CodeUnit.PLATE_COMMENT, comment);
    }
}
