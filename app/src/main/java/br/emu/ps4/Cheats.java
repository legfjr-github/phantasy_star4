package br.emu.ps4;

/**
 * Códigos Game Genie de Phantasy Star IV (USA), criados por Tony Hedstrom
 * (lista v0.8, 28/04/2007, angelfire.com/games2/codehut). Nomes resumidos em português.
 * Códigos do mesmo grupo alteram o mesmo ponto da ROM: só um pode ficar ativo.
 */
final class Cheats {
    static final class Cheat {
        final String category, name, code, group;

        Cheat(String category, String name, String code, String group) {
            this.category = category;
            this.name = name;
            this.code = code;
            this.group = group;
        }

        String key() { return "cheat_" + code; }
    }

    private static final String XP = "Experiência e batalha";
    private static final String MONEY = "Meseta e lojas";
    private static final String ITEMS = "Itens";
    private static final String START = "Início de jogo novo (ative antes de começar)";
    private static final String TP = "Técnicas custando 1 TP";
    private static final String TECH = "Técnicas mais fortes";
    private static final String SKILL = "Skills mais fortes";

    static final Cheat[] ALL = {
            new Cheat(XP, "Mais XP depois das batalhas", "RE2A-A6V4", "xp"),
            new Cheat(XP, "Muito mais XP depois das batalhas", "2J2A-AFV4", "xp"),
            new Cheat(XP, "Todos sobem para o nível 99 após 1 batalha", "BA2A-AA5G", "xp"),
            new Cheat(XP, "TP infinito fora de batalha", "AJJT-NA4G", null),
            new Cheat(XP, "TP infinito em batalha", "ALJT-AA6N", null),
            new Cheat(XP, "Skills infinitas em batalha", "ALRA-AA4E", null),
            new Cheat(XP, "Sempre ganhar item após batalha", "A22T-AA5Y", null),

            new Cheat(MONEY, "Meseta x2 nos baús", "3B0A-NADW", "chest"),
            new Cheat(MONEY, "Meseta x10 nos baús", "7B0A-NGDW", "chest"),
            new Cheat(MONEY, "Hahn dá 50.000 meseta (em vez de 100)", "LC4A-NHYL", null),
            new Cheat(MONEY, "Lojas não cobram (precisa ter o dinheiro)", "AKNT-NA9R", "shop"),
            new Cheat(MONEY, "Tudo grátis nas lojas", "AKNT-NA9R+RFKT-N6WW", "shop"),

            new Cheat(ITEMS, "Abrir baús quantas vezes quiser", "AWFT-LA54", null),
            new Cheat(ITEMS, "Monomate ~3x mais forte", "WCNC-ZEGT", "monomate"),
            new Cheat(ITEMS, "Monomate ~10x mais forte", "8CNC-ZEGT+8CNC-YJGW", "monomate"),
            new Cheat(ITEMS, "Monomate cura 260+ HP em todos", "98NC-YLGW", "monomate"),
            new Cheat(ITEMS, "Monomate cura 500+ HP em todos", "98NC-ZEGT+98NC-YLGW", "monomate"),
            new Cheat(ITEMS, "Dimate funciona em todos", "GCNC-YLHJ", "dimate"),
            new Cheat(ITEMS, "Dimate em todos e mais forte", "98NC-YLHJ", "dimate"),
            new Cheat(ITEMS, "Antidote funciona em todos", "ACNW-YLAY", null),
            new Cheat(ITEMS, "Cure-Paral funciona em todos", "ACNW-YLBL", null),

            new Cheat(START, "Começar com 1.000 meseta", "7BCA-JGFY", "startmeseta"),
            new Cheat(START, "Começar com 10.000 meseta", "CBCA-JRPY", "startmeseta"),
            new Cheat(START, "Começar com 50.000 meseta", "LBCA-JHZY", "startmeseta"),
            new Cheat(START, "Começar com 262.644 meseta", "AVCA-JAFW", "startmeseta"),
            new Cheat(START, "Chaz começa no nível 7", "BGFC-YWGT", "startlvl"),
            new Cheat(START, "Chaz começa no nível 18", "LLFC-YZRT", "startlvl"),
            new Cheat(START, "Chaz começa no nível 27", "ALFC-YAGR", "startlvl"),
            new Cheat(START, "Chaz começa com Titanium Sword", "ACFC-ZEHJ", "weapon"),
            new Cheat(START, "Chaz começa com Guard Sword", "ACFC-Y49J", "weapon"),
            new Cheat(START, "Chaz começa com Elsydeon", "ACFC-ZR9J", "weapon"),
            new Cheat(START, "Chaz começa com Titanium Helmet e Ceramic Armor", "GGFC-ZWHL", "armor"),
            new Cheat(START, "Chaz começa com Silver Helmet e Guard Mail", "R0FC-YW1L", "armor"),

            new Cheat(TP, "Res", "AGRC-ZEFA", null),
            new Cheat(TP, "GiRes", "AGRC-ZEFJ", null),
            new Cheat(TP, "NaRes", "AGRC-ZEFT", null),
            new Cheat(TP, "Sar", "AGRC-ZEF2", null),
            new Cheat(TP, "GiSar", "AGRC-ZEGA", null),
            new Cheat(TP, "NaSar", "AGRC-ZEGJ", null),
            new Cheat(TP, "Megid", "AGRC-YCDA", null),
            new Cheat(TP, "Tsu", "AGRC-YCA2", null),
            new Cheat(TP, "GiThu", "AGRC-YCBA", null),
            new Cheat(TP, "NaThu", "AGRC-YCBJ", null),
            new Cheat(TP, "Foi", "AGPW-YCHJ", null),
            new Cheat(TP, "GiFoi", "AGPW-YCHT", null),
            new Cheat(TP, "NaFoi", "AGPW-YCH2", null),
            new Cheat(TP, "Zan", "AGRC-YCBT", null),
            new Cheat(TP, "GiZan", "AGRC-YCB2", null),
            new Cheat(TP, "NaZan", "AGRC-YCCA", null),
            new Cheat(TP, "Rever", "AGRW-ZLAA", null),

            new Cheat(TECH, "Res mais forte", "LCRC-ZJPC", "res"),
            new Cheat(TECH, "Res muito mais forte", "8CRC-ZJPC", "res"),
            new Cheat(TECH, "Res mais forte, em todos", "JCRC-ZLPC", "res"),
            new Cheat(TECH, "Res muito mais forte, em todos", "8CRC-ZLPC", "res"),
            new Cheat(TECH, "GiRes muito mais forte", "8CRC-ZJPL", "gires"),
            new Cheat(TECH, "GiRes muito mais forte, em todos", "8CRC-ZLPL", "gires"),
            new Cheat(TECH, "NaRes em todos", "8CRC-ZLPW", null),
            new Cheat(TECH, "Sar muito mais forte", "8CRC-ZLP4", null),
            new Cheat(TECH, "GiSar muito mais forte", "8CRC-ZLRC", null),
            new Cheat(TECH, "NaSar mais forte", "8CRC-ZLRL", null),
            new Cheat(TECH, "Rever em todos (não testado pelo autor)", "ACRW-ZLJC", "rever"),
            new Cheat(TECH, "Rever em todos e mais forte (não testado pelo autor)", "8CRW-ZLJC", "rever"),
            new Cheat(TECH, "Shift em todos", "ACRC-ZWGW", null),
            new Cheat(TECH, "Tsu muito mais forte", "8CRC-ZCA4", "tsu"),
            new Cheat(TECH, "Tsu em todos os inimigos", "GCRC-ZEA4", "tsu"),
            new Cheat(TECH, "Tsu em todos e muito mais forte", "8CRC-ZEA4", "tsu"),
            new Cheat(TECH, "GiThu em todos os inimigos", "NCRC-ZEBC", "githu"),
            new Cheat(TECH, "GiThu em todos e muito mais forte", "8CRC-ZEBC", "githu"),
            new Cheat(TECH, "NaThu em todos e muito mais forte", "8CRC-ZEBL", null),
            new Cheat(TECH, "Foi muito mais forte", "8CPW-ZCHL", "foi"),
            new Cheat(TECH, "Foi em todos os inimigos", "DCPW-ZEHL", "foi"),
            new Cheat(TECH, "Foi em todos e muito mais forte", "8CPW-ZEHL", "foi"),
            new Cheat(TECH, "GiFoi em todos os inimigos", "KCPW-ZEHW", "gifoi"),
            new Cheat(TECH, "GiFoi em todos e muito mais forte", "8CPW-ZEHW", "gifoi"),
            new Cheat(TECH, "NaFoi em todos os inimigos", "VCPW-ZEH4", "nafoi"),
            new Cheat(TECH, "NaFoi em todos e muito mais forte", "8CPW-ZEH4", "nafoi"),
            new Cheat(TECH, "Zan muito mais forte", "8CRC-ZEBW", null),
            new Cheat(TECH, "GiZan muito mais forte", "8CRC-ZEB4", null),
            new Cheat(TECH, "NaZan muito mais forte", "8CRC-ZECC", null),

            new Cheat(SKILL, "Earth em todos os inimigos", "ECSC-ZEA4", null),
            new Cheat(SKILL, "Crosscut muito mais forte", "8CRW-ZCBL", "crosscut"),
            new Cheat(SKILL, "Crosscut em todos os inimigos", "LCRW-ZEBL", "crosscut"),
            new Cheat(SKILL, "Crosscut em todos e muito mais forte", "8CRW-ZEBL", "crosscut"),
            new Cheat(SKILL, "Airslash muito mais forte", "8CRW-ZEDC", null),
            new Cheat(SKILL, "Vortex muito mais forte", "8CRW-ZCCW", "vortex"),
            new Cheat(SKILL, "Vortex em todos os inimigos", "GCRW-ZECW", "vortex"),
            new Cheat(SKILL, "Vortex em todos e muito mais forte", "8CRW-ZECW", "vortex"),
            new Cheat(SKILL, "Rayblade em todos os inimigos", "0CRW-ZEBW", "rayblade"),
            new Cheat(SKILL, "Rayblade em todos e mais forte", "8CRW-ZEBW", "rayblade"),
    };

    private Cheats() {}
}
