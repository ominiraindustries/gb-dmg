"""Generate games/faro/design/screens/*.screen (ui-designer). Boxes come from helpers so rows are
always 20 chars; texts use '.' for blanks. Run, then `python harness/gb.py preview faro`."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "games/faro/design/screens"
sys.path.insert(0, str(ROOT / "harness"))
import asciitiles  # noqa: E402

FONT_LABELS = asciitiles.parse(ROOT / "harness/common/font.tiles")[1]
ES_LABELS = asciitiles.parse(ROOT / "harness/common/font_es.tiles")[1]

# ------------------------------------------------------------------ legend (symbol -> tile)
LEGEND = {
    # ui.tiles (resident)
    "<": "ui:FRAME_TL", "_": "ui:FRAME_T", ">": "ui:FRAME_TR", "{": "ui:FRAME_L", "}": "ui:FRAME_R",
    "(": "ui:FRAME_BL", "=": "ui:FRAME_B", ")": "ui:FRAME_BR", "*": "ui:CURSOR", "▼": "ui:ARROW_DOWN",
    "$": "ui:COIN",
    # uibattle.tiles
    "[": "uimenu:BAR_L", "]": "uimenu:BAR_R", "□": "uimenu:BAR_0", "▏": "uimenu:BAR_1",
    "▎": "uimenu:BAR_2", "▍": "uimenu:BAR_3", "▌": "uimenu:BAR_4", "▋": "uimenu:BAR_5",
    "▊": "uimenu:BAR_6", "▉": "uimenu:BAR_7", "■": "uimenu:BAR_8",
    "Ω": "uimenu:BOWL_FULL", "Ψ": "uimenu:BOWL_MID", "Φ": "uimenu:BOWL_LOW", "Θ": "uimenu:BOWL_EMPTY",
    "#": "uimenu:ST_NET", "~": "uimenu:ST_CALM", "☼": "uimenu:ST_LIT", "^": "uimenu:ST_FLY",
    "»": "uimenu:CURSOR_IDLE", "▲": "uimenu:ARROW_UP", "+": "uimenu:PLUS",
    # uiscreen.tiles
    "α": "uimenu:POCKET_ITEMS", "β": "uimenu:POCKET_FOOD", "γ": "uimenu:POCKET_GADGETS",
    "δ": "uimenu:POCKET_LANTERNS", "ε": "uimenu:FAM_BICHO", "ζ": "uimenu:FAM_BESTIA",
    "η": "uimenu:FAM_AVE", "θ": "uimenu:FAM_PEZ", "ι": "uimenu:FAM_REPTIL", "κ": "uimenu:FAM_FLORA",
    "λ": "uimenu:FAM_BRUMA", "μ": "uimenu:DMG_CORTE", "ν": "uimenu:DMG_GOLPE",
    "ξ": "uimenu:DMG_PUNTA", "π": "uimenu:DMG_FUEGO", "●": "uimenu:MARK_CAUGHT",
    "○": "uimenu:MARK_SEEN", "ρ": "uimenu:POT", "◀": "uimenu:ARROW_LEFT", "▶": "uimenu:ARROW_RIGHT",
    # font punctuation
    "/": "font:SLASH", ":": "font:COLON", "!": "font:EXCLAM", "?": "font:QUESTION", "-": "font:DASH",
    "·": "font:DOT",
}
# Spanish punctuation: harness/common/font_es.tiles (E14)
for ch, lab in ((",", "COMMA"), ("'", "APOSTROPHE"), ("¡", "EXCL_OPEN"), ("¿", "QUEST_OPEN")):
    if lab in ES_LABELS:
        LEGEND[ch] = f"font_es:{lab}"
MISSING_PUNCT = [c for c in ",'¡¿" if c not in LEGEND]



class Screen:
    def __init__(self, name, sets, header):
        self.name, self.sets, self.header = name, sets, header
        self.g = [["."] * 20 for _ in range(18)]
        self.sprites = []

    def put(self, r, c, ch):
        assert 0 <= r < 18 and 0 <= c < 20, (self.name, r, c, ch)
        self.g[r][c] = ch

    def text(self, r, c, s):
        assert c + len(s) <= 20, (self.name, r, c, s)
        for i, ch in enumerate(s):
            if ch in MISSING_PUNCT:
                ch = "."                      # glyph not in the font yet: blank cell
            self.put(r, c + i, "." if ch == " " else ch)

    def box(self, r0, c0, r1, c1, tab=None, open_right=False, fill=True):
        """Frame from (r0,c0) to (r1,c1) inclusive. open_right: no right border (drawer)."""
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                top, bot, left, right = r == r0, r == r1, c == c0, c == c1 and not open_right
                ch = "." if fill else self.g[r][c]
                if top:
                    ch = "<" if left else (">" if right else "_")
                elif bot:
                    ch = "(" if left else (")" if right else "=")
                elif left:
                    ch = "{"
                elif right:
                    ch = "}"
                self.put(r, c, ch)
        if tab:
            self.text(r0, c0 + 2, " " + tab + " ")

    def hline(self, r, c0, c1, ch="_"):
        for c in range(c0, c1 + 1):
            self.put(r, c, ch)

    def bar(self, r, c, px):
        """BAR_L + 8 fill tiles (px of 64) + BAR_R at (r, c..c+9)."""
        fills = "□▏▎▍▌▋▊▉■"
        self.put(r, c, "[")
        for i in range(8):
            self.put(r, c + 1 + i, fills[max(0, min(8, px - 8 * i))])
        self.put(r, c + 9, "]")

    def spr(self, ref, x, y, tall=True, comment=None):
        """8x16 sprite: listed as two 8x8 halves for the preview (ref = set:index of the top)."""
        if comment:
            self.sprites.append("; " + comment)
        s, i = ref.split(":")
        i = int(i)
        self.sprites.append(f"{s}:{i} {x} {y}")
        if tall:
            self.sprites.append(f"{s}:{i + 1} {x} {y + 8}")

    def player(self, x=64, y=64):
        self.spr("leo:0", x, y, comment="Leo (pixel-artist leo.tiles DOWN_A), 16x16 at the camera spot (64, 64)")
        self.spr("leo:2", x + 8, y)

    def write(self):
        rows = ["".join(r) for r in self.g]
        used = sorted({ch for row in rows for ch in row if ch in LEGEND})
        lines = list(self.header) + [f"tilesets: {' '.join(self.sets)} font font_lower font_es", "legend:"]
        for ch in used:
            lines.append(f"{ch} {LEGEND[ch]}")
        lines.append("grid:")
        for row in rows:
            assert len(row) == 20
            lines.append(row)
        lines.append("sprites:")
        lines += self.sprites
        (OUT / f"{self.name}.screen").write_text("\n".join(lines) + "\n", encoding="utf-8")


def S(name, sets, *header):
    return Screen(name, sets, ["; " + h if h else ";" for h in header])


screens = []

# ================================================================== FIELD HUD
s = S("campo_hud", ["ui"],
      "FIELD (M1b). The map is the world engine's BG (blank here). No HUD tiles: two 8x16 sprites,",
      "OAM 0 heart at (4, 4) and OAM 1 bowl at (14, 4), from the 2 HUD slots (uispr.tiles). Each is",
      "hidden (y = 0) while its value is 'fine' (PV >= 50 %, sac >= 60), shown 180 f after any band",
      "change, the empty states blink 16/16 f. Shown here: PV < 50 % and sac 25-59. See ui.md 3.")
s.player()
s.spr("uispr:2", 4, 4, comment="HUD heart (HEART_HALF state copied into the heart slot)")
s.spr("uispr:8", 14, 4, comment="HUD bowl (BOWL_HALF state copied into the bowl slot)")
screens.append(s)

# ================================================================== DIALOGUE (window)
def dialog_base(name, *hdr, speaker="Tomasa"):
    s = S(name, ["ui"], *hdr)
    s.box(12, 0, 17, 19, tab=speaker)
    s.player()
    return s


s = dialog_base("dialogo",
                "DIALOGUE (M1b): window, WY = 96 (screen rows 12-17), WX = 7. Window map row = screen",
                "row - 12. Speaker name in a tab on the top border (cols 3.., blank before/after; no",
                "speaker = plain border). 2 lines of 18 chars: rows 14 and 16, cols 1-18. 'More' arrow:",
                "ARROW_DOWN replaces the FRAME_B at row 17 col 17, blinking 16/16 f with FRAME_B while the",
                "box waits for A/B. Typewriter 1 char/f (Opciones), 4 tiles/f max. See ui.md 4.")
s.text(14, 1, "¡Leo! Tu abuela me")
s.text(16, 1, "dejo esto para ti·")
s.put(17, 17, "▼")
screens.append(s)

s = dialog_base("dialogo_sino",
                "ASK (M1b): yes/no inside the dialogue box. The question is ONE line (row 14, <= 18",
                "chars; longer context goes in a SAY page before). Row 16: 'Si' and 'No' on the right,",
                "cursor at col 12 (Si) or col 16 (No); starts on Si (No for dangerous questions: the",
                "script says which). Up/down/left/right toggle, A confirms, B = No.")
s.text(14, 1, "¿Cocinamos algo?")
s.put(16, 12, "*")
s.text(16, 13, "Si")
s.text(16, 17, "No")
screens.append(s)

s = dialog_base("dialogo_elige",
                "CHOICE of 3-4 (M1b): the question was the previous page; the box shows the options in",
                "2 columns x 2 rows: cursor cols 1 / 10, text cols 2-9 / 11-18 (<= 8 chars), rows 14/16.",
                "Order: left-top, right-top, left-bottom, right-bottom. B = last option (Salir).",
                speaker="Rosa")
s.put(14, 1, "*")
s.text(14, 2, "Comprar")
s.text(14, 11, "Vender")
s.text(16, 2, "Hablar")
s.text(16, 11, "Salir")
screens.append(s)

s = dialog_base("dialogo_cartel",
                "SIGN / no speaker (M1b): same box with a plain top border (no tab). Shown: the last",
                "page, no arrow (A/B closes).", speaker=None)
s.text(14, 1, "Varadero")
s.text(16, 1, "Muelle de pesca")
screens.append(s)

# ================================================================== START PANEL (window, drawer)
def panel_base(name, *hdr):
    s = S(name, ["ui"], *hdr)
    s.player()
    s.box(0, 10, 17, 19, open_right=True)
    return s


s = panel_base("panel",
               "START PANEL (M1b): window WX = 87 (screen cols 10-19), WY = 0, slides in WX 167 -> 87 in",
               "8 f (10 px/f) and out the same way. Window map col = screen col - 10. A drawer: left",
               "border only, top/bottom lines run to the screen edge. Entries rows 1-8 (1-row pitch,",
               "checked: no descender touches a letter below), cursor col 11, text cols 12-19.",
               "'Mapa' is M2: in M1 the list has 7 entries and rows shift up (row = 1 + index).",
               "Stats rows 10-15: HUD sprites move in as labels (heart = PV, bowl = saciedad).")
for i, e in enumerate(["Cuaderno", "Mochila", "Equipo", "Acampar", "Mapa", "Guardar", "Opciones", "Salir"]):
    s.text(1 + i, 12, e)
s.put(1, 11, "*")
s.text(10, 11, "Leo")
s.text(11, 11, "Nv")
s.text(11, 18, "12")
s.text(12, 15, "32/38")
s.text(13, 11, "EN   9/13")
s.text(14, 13, "Normal")
s.put(15, 11, "$")
s.text(15, 16, "1250")
s.text(16, 11, "Dia")
s.spr("uispr:2", 88, 96, comment="OAM 0 (HUD heart) moved to the panel PV row while it is open")
s.spr("uispr:8", 88, 112, comment="OAM 1 (HUD bowl) moved to the panel saciedad row")
screens.append(s)

s = panel_base("panel_guardar",
               "SAVE from the panel (M1b): the stats area (rows 10-16) becomes the save box. Rows 10-13:",
               "name, 'Luces' (registered species), play time (h:mm, up to 99:59). Row 15 question,",
               "row 16 Si/No (cursor col 12 or 16, starts on Si). After A on Si: row 15 'Guardando',",
               "SFX SAVE, then 'Guardado' 60 f and back to the stats. B = No.")
for i, e in enumerate(["Cuaderno", "Mochila", "Equipo", "Acampar", "Mapa", "Guardar", "Opciones", "Salir"]):
    s.text(1 + i, 12, e)
s.put(6, 11, "»")
s.text(10, 11, "Leo")
s.text(11, 11, "Luces   5")
s.text(12, 11, "Tiempo")
s.text(13, 16, "1:23")
s.text(15, 11, "¿Guardar?")
s.put(16, 12, "*")
s.text(16, 13, "Si")
s.text(16, 17, "No")
s.sets = ["ui", "uimenu"]
screens.append(s)

s = panel_base("panel_aviso",
               "PANEL MESSAGE (M1b): refusals from the panel are written in the stats area (rows 10-16,",
               "cols 11-19, 9 chars per line, 1-row pitch) for 90 f or until A/B: 'No es seguro' (creature",
               "alert near), 'Aqui no' (town / no CAMP cell), 'Sin madera' (no firewood).")
for i, e in enumerate(["Cuaderno", "Mochila", "Equipo", "Acampar", "Mapa", "Guardar", "Opciones", "Salir"]):
    s.text(1 + i, 12, e)
s.put(4, 11, "*")
s.text(11, 11, "No es")
s.text(12, 11, "seguro:")
s.text(13, 11, "hay algo")
s.text(14, 11, "cerca·")
screens.append(s)

# ================================================================== BATTLE
def battle_base(name, *hdr):
    s = S(name, ["ui", "uimenu"], *hdr)
    # enemy block: half frame (left line + bottom line), cols 0-12 rows 1-4
    for r in (1, 2, 3):
        s.put(r, 0, "{")
    s.put(4, 0, "(")
    s.hline(4, 1, 12, "=")
    s.text(1, 1, "Pinzarro")
    s.text(2, 1, "Nv3")
    s.text(2, 6, "DOR")
    s.put(2, 10, "~")
    s.text(3, 1, "PV")
    s.bar(3, 3, 12)
    # player block: half frame (right line + bottom line), cols 6-19 rows 7-11
    for r in (7, 8, 9, 10):
        s.put(r, 19, "}")
    s.put(11, 19, ")")
    s.hline(11, 6, 18, "=")
    s.text(7, 7, "Leo")
    s.text(7, 16, "Nv5")
    s.text(8, 7, "PV")
    s.bar(8, 9, 54)
    s.text(9, 7, "VEN")
    s.text(9, 14, "32/38")
    s.text(10, 7, "EN")
    s.text(10, 11, "9/13")
    s.put(10, 18, "Ψ")
    return s


s = battle_base("combate",
                "BATTLE, command menu (M1b). All BG, LCD-off build inside the fade (GDD 3.1), window off.",
                "Creature picture 7x7 at cols 13-19 rows 0-6 and player back 5x6 at cols 1-5 rows 7-12",
                "are written by the code from the .pic data (blank here). Enemy block: name row 1, level",
                "+ status (3 letters) + flag icons row 2, PV bar row 3, half frame. Player block: name +",
                "level row 7, PV bar row 8, status + PV numbers row 9, EN + bowl row 10. Menu box rows",
                "13-17: 3 x 2 commands, cursor cols 1 / 9, text cols 2 / 10. See ui.md 6.")
s.box(13, 0, 17, 19)
s.put(14, 1, "*")
s.text(14, 2, "Atacar")
s.text(14, 10, "Tecnica")
s.text(15, 2, "Objeto")
s.text(15, 10, "Artilugio")
s.text(16, 2, "Huir")
s.text(16, 10, "Capturar")
screens.append(s)

s = battle_base("combate_msg",
                "BATTLE message (M1b): the menu box shows 2 lines (rows 14 and 16, 18 chars), typed at",
                "2 chars/f. ARROW_DOWN at row 17 col 17 blinks when the line waits for A (only on",
                "messages that need reading; the turn sequence auto-advances after 40 f otherwise).")
s.box(13, 0, 17, 19)
s.text(14, 1, "¡Golpe suave! Le")
s.text(16, 1, "quedan 3 PV·")
s.put(17, 17, "▼")
screens.append(s)


def battle_sub(name, tab, rows, *hdr, detail=None, more_up=False, more_down=False):
    s = battle_base(name, *hdr)
    s.box(13, 0, 17, 19, tab=tab)
    for i, (label, right) in enumerate(rows):
        s.text(14 + i, 2, label)
        if right:
            s.text(14 + i, 19 - len(right), right)
    s.put(14, 1, "*")
    if more_up:
        s.put(13, 17, "▲")
    if more_down:
        s.put(17, 17, "▼")
    if detail:
        # detail box replaces the player block (cols 6-19 rows 7-11 -> framed cols 6-19 rows 6-12)
        for r in range(7, 12):
            for c in range(6, 20):
                s.put(r, c, ".")
        s.box(6, 6, 12, 19)
        for i, line in enumerate(detail):
            if line:
                s.text(7 + i, 7, line)
    return s


s = battle_sub("combate_atacar", "Atacar",
               [("Cuchillo", ""), ("Remo viejo", ""), ("Machete", "")],
               "BATTLE > Atacar (M1b): the 3 weapons of the bag (Equipo), tab 'Atacar' on the box border.",
               "Names cols 2-15 (<= 14). The detail box (cols 6-19 rows 6-12) covers the player block",
               "while a list is open and shows the selected weapon: type icon + name row 7, 'Poder' row 8,",
               "efficacy row 9 ('Eficaz', 'Poco eficaz', 'No le afecta', blank = unknown or normal;",
               "known after Ojo de farero or once captured). B: back to the commands (cursor on Atacar).",
               detail=["μ Corte", "Poder   8", "Poco eficaz"])
s.sets = ["ui", "uimenu"]
screens.append(s)

s = battle_sub("combate_tecnica", "Tecnica",
               [("Golpe suave", "2"), ("Concentrar", "0"), ("Ojo de farero", "1")],
               "BATTLE > Tecnica (M1b): learned techniques, cost in EN right-aligned cols 17-18; 3",
               "visible, scrolls one at a time; ARROW_UP (row 13 col 17) / ARROW_DOWN (row 17 col 17)",
               "while there is more above / below. Not enough EN: the cost blinks 8/8 f and A gives",
               "SFX BACK. Detail box: 'Coste' + 'EN' now/max, then a 2-line blurb (12 chars).",
               detail=["Coste  2 EN", "Tienes  9/13", "Nunca deja a", "0 PV"], more_down=True)
screens.append(s)

s = battle_sub("combate_objeto", "Objeto",
               [("Pocion", "3"), ("Antidoto", "1"), ("Asado simple", "2")],
               "BATTLE > Objeto / Artilugio / Capturar (M1b): same list, tab = the command, count",
               "right-aligned cols 17-18. Capturar lists lantern types; Artilugio the battle gadgets",
               "(key gadgets show no count). Detail box: 'Tienes' + 3-line blurb (12 chars).",
               detail=["Tienes  3", "Cura 30 PV·", "", ""], more_down=True)
screens.append(s)

s = battle_base("combate_nivel",
                "BATTLE level up (M1b): after the victory messages, a box over the (gone) creature area,",
                "cols 8-19 rows 0-6, tab with the new level; gains with PLUS, right-aligned cols 17-18.",
                "The message box says 'Leo sube al Nv6!'. A closes; then 'Aprende ...' messages.")
for r in range(0, 5):
    for c in range(0, 13):
        s.put(r, c, ".")
s.box(0, 8, 6, 19, tab="Nv6")
for i, (lab, v) in enumerate((("PV", "+4"), ("EN", "+1"), ("ATQ", "+2"), ("DEF", "+1"), ("AGI", "+1"))):
    s.text(1 + i, 9, lab)
    s.put(1 + i, 19 - len(v), "+")
    s.text(1 + i, 20 - len(v), v[1:])
s.box(13, 0, 17, 19)
s.text(14, 1, "¡Leo sube al Nv6!")
s.put(17, 17, "▼")
screens.append(s)

# ================================================================== MOCHILA
s = S("mochila", ["ui", "uimenu"],
      "MOCHILA (M1b), full screen, LCD-off build. Header row 1: pocket arrows (cols 1 and 18),",
      "pocket icon col 3, pocket name cols 5-14. Left/right change pocket (Objetos, Comida,",
      "Artilugios, Farolillos) and redraw the list. List rows 4-11 (8 visible, 1-row pitch): cursor",
      "col 1, name cols 2-15, count right-aligned cols 17-18 ('Sel' = gadget registered on Select).",
      "ARROW_UP row 3 col 17 / ARROW_DOWN row 12 col 17 when the list scrolls. Info box rows 13-17:",
      "item icon 16x16 at cols 1-2 rows 14-15 (pixel-artist icons, 4 tiles at $8800) and a 2-line",
      "description cols 4-18 rows 14 and 16 (15 chars). A: action popup. B: back to the panel.",
      "Start: sort the pocket (by kind, then name).")
s.box(0, 0, 2, 19)
s.put(1, 1, "◀")
s.put(1, 3, "β")
s.text(1, 5, "Comida")
s.put(1, 18, "▶")
s.box(3, 0, 12, 19)
for i, (n, c) in enumerate((("Carne cangrejo", "2"), ("Muslo conejo", "1"), ("Bayas", "5"),
                            ("Sal", "3"), ("Pan", "1"), ("Asado simple", "2"), ("Huevo gaviota", "4"),
                            ("Caldo de algas", "1"))):
    s.text(4 + i, 2, n[:14])
    if c:
        s.text(4 + i, 19 - len(c), c)
s.put(4, 1, "*")
s.put(12, 17, "▼")
s.box(13, 0, 17, 19)
s.text(14, 4, "Carne fresca·")
s.text(16, 4, "Se estropea·")
screens.append(s)

s = S("mochila_accion", ["ui", "uimenu"],
      "MOCHILA action popup (M1b): BG box cols 8-19 rows 6-12 over the list (the code saves",
      "nothing: it redraws the list rows when the popup closes). Options rows 7-11 (1-row pitch),",
      "cursor col 9, text cols 10-18 (<= 9). Per pocket: Objetos 'Usar Tirar Salir', Comida",
      "'Comer Tirar Salir', Artilugios 'Usar Registrar Tirar Salir' (Tirar only for consumables),",
      "Farolillos 'Tirar Salir'. B = Salir. Tirar asks the amount with the quantity box (tienda).",
      "The list cursor stays as CURSOR_IDLE.")
s.box(0, 0, 2, 19)
s.put(1, 1, "◀")
s.put(1, 3, "γ")
s.text(1, 5, "Artilugios")
s.put(1, 18, "▶")
s.box(3, 0, 12, 19)
for i, (n, c) in enumerate((("Honda", "Sel"), ("Red", "4"), ("Cebo dulce", "2"), ("Bengala", "1"))):
    s.text(4 + i, 2, n)
    s.text(4 + i, 19 - len(c), c)
s.put(5, 1, "»")
s.box(6, 8, 12, 19)
for i, o in enumerate(("Usar", "Registrar", "Tirar", "Salir")):
    s.text(7 + i, 10, o)
s.put(8, 9, "*")
s.box(13, 0, 17, 19)
s.text(14, 4, "Enreda a la")
s.text(16, 4, "presa 3 turnos·")
screens.append(s)

# ================================================================== CUADERNO
s = S("cuaderno", ["ui", "uimenu"],
      "CUADERNO list (M1b: 6 species, full game 48). Header row 1: title cols 1-8, lantern icon",
      "col 13, caught count right-aligned cols 15-18 ('5/48'). List rows 4-13 (10 visible, 1-row",
      "pitch): cursor col 1, number cols 2-3, marker col 5 (MARK_CAUGHT capturada / MARK_SEEN",
      "vista / blank unknown), name cols 7-16 or '-----' if unknown. Scroll arrows row 3 / row 14",
      "col 17. Footer row 16: family icon col 1 + family name cols 3-8, 'Cazas' + kills",
      "right-aligned cols 17-18 (blank for unknown species). A: ficha (seen species only). B: panel.")
s.box(0, 0, 2, 19)
s.text(1, 1, "Cuaderno")
s.put(1, 13, "δ")
s.text(1, 15, "5/48")
s.box(3, 0, 14, 19)
mons = [("01", "●", "Pinzarro"), ("02", "●", "Dunejo"), ("03", "○", "Gavirata"), ("04", "●", "Sapoyo"),
        ("05", "●", "Erizal"), ("06", "●", "Polifaro"), ("07", "○", "Zancuda"), ("08", "", "-----"),
        ("09", "", "-----"), ("10", "", "-----")]
for i, (n, m, nm) in enumerate(mons):
    s.text(4 + i, 2, n)
    if m:
        s.put(4 + i, 5, m)
    s.text(4 + i, 7, nm)
s.put(4, 1, "*")
s.put(14, 17, "▼")
s.box(15, 0, 17, 19)
s.put(16, 1, "ε")
s.text(16, 3, "Bicho")
s.text(16, 11, "Cazas")
s.text(16, 18, "3")
screens.append(s)

s = S("cuaderno_ficha", ["ui", "uimenu"],
      "CUADERNO entry page (M1b). Picture 7x7 (code, from the .pic, tiles at $8800) inside the",
      "frame cols 0-8 rows 0-8. Right: name row 1 (cols 10-19), number row 2, family icon + name",
      "row 3, 'Debil' row 4 and 'Resiste' row 5 (or 'Inmune' for BRUMA) with damage-type icons",
      "right-aligned ending col 19 ('?' icons until known: Ojo de farero or captured), 'Cazas' row",
      "6. Box rows 9-17: 'Zona' and 'Cebo' rows 10-11 (values cols 7-18), description rows 13-15",
      "(3 lines x 18, 1-row pitch), kitchen note row 16 (POT icon col 1, text cols 3-18). Only",
      "captured species show the description and note (seen: rows 13-16 '???'). Up/down: previous /",
      "next seen species. B: back to the list.")
s.box(0, 0, 8, 8)
s.text(1, 10, "Pinzarro")
s.text(2, 10, "01")
s.put(2, 13, "●")
s.put(3, 10, "ε")
s.text(3, 12, "Bicho")
s.text(4, 10, "Debil")
s.put(4, 19, "ν")
s.text(5, 10, "Resiste")
s.put(5, 19, "μ")
s.text(6, 10, "Cazas")
s.text(6, 18, "3")
s.box(9, 0, 17, 19)
s.text(10, 1, "Zona")
s.text(10, 7, "Playa")
s.text(11, 1, "Cebo")
s.text(11, 7, "Pescado")
s.text(13, 1, "Anda de lado y")
s.text(14, 1, "pellizca a quien")
s.text(15, 1, "pisa su arena·")
s.put(16, 1, "ρ")
s.text(16, 3, "Con sal, un lujo·")
screens.append(s)

# ================================================================== EQUIPO
def equipo_header(s):
    s.box(0, 0, 2, 19)
    s.put(1, 1, "◀")
    s.text(1, 3, "Leo")
    s.text(1, 9, "VEN")
    s.text(1, 15, "Nv3")
    s.put(1, 18, "▶")


s = S("equipo", ["ui", "uimenu"],
      "EQUIPO page 1 'Estado' (M1b). Header row 1: page arrows cols 1/18, name cols 3-7, status",
      "(3 letters, blank if none) cols 9-11, level cols 14-17. Stats rows 4-7: labels cols 1-2 /",
      "13-15, values right-aligned ending col 10 / col 18; row 6 bowl icon + band word; row 7 PX",
      "bar to the next level. Gear box rows 8-13: 3 weapon slots rows 9-11 (name cols 2-15, type",
      "icon col 18, '-' if empty), clothes row 12 (name, '+n' DEF right-aligned cols 16-18).",
      "Footer rows 14-17: row 15 detail of the selected gear, row 16 active dish (POT icon,",
      "buff name, steps left right-aligned). A on a slot: list of owned weapons/clothes to swap",
      "(same box as MOCHILA's popup, wider). Left/right: page 2 (Tecnicas). B: back.")
equipo_header(s)
s.box(3, 0, 8, 19)
s.text(4, 1, "PV")
s.text(4, 6, "26/30")
s.text(4, 13, "ATQ")
s.text(4, 18, "8")
s.text(5, 1, "EN")
s.text(5, 6, "11/11")
s.text(5, 13, "DEF")
s.text(5, 18, "7")
s.put(6, 1, "Ψ")
s.text(6, 3, "Normal")
s.text(6, 13, "AGI")
s.text(6, 18, "8")
s.text(7, 1, "PX")
s.bar(7, 3, 40)
s.box(8, 0, 13, 19)
s.put(8, 0, "{")
s.put(8, 19, "}")
for i, (n, ic) in enumerate((("Cuchillo", "μ"), ("Remo viejo", "ν"), ("Machete", "μ"))):
    s.text(9 + i, 2, n)
    s.put(9 + i, 18, ic)
s.text(12, 2, "Chubasquero")
s.put(12, 17, "+")
s.text(12, 18, "3")
s.put(9, 1, "*")
s.box(14, 0, 17, 19)
s.text(15, 1, "Corte  Poder  8")
s.put(16, 1, "ρ")
s.text(16, 3, "Coraza")
s.text(16, 16, "384")
screens.append(s)

s = S("equipo_tecnicas", ["ui", "uimenu"],
      "EQUIPO page 2 'Tecnicas' (M1b). Same header. List rows 4-12 (9 visible): name cols 2-15,",
      "EN cost right-aligned cols 17-18. Footer rows 14-17: 2-line description rows 15 and 16 (18",
      "chars). A on a technique usable out of battle (Primeros auxilios, Concentrar): use it.")
equipo_header(s)
s.box(3, 0, 13, 19, tab="Tecnicas")
for i, (n, c) in enumerate((("Concentrar", "0"), ("Ojo de farero", "1"), ("Golpe suave", "2"),
                            ("Aturdir", "3"), ("Primeros aux", "5"), ("Silbido", "3"))):
    s.text(4 + i, 2, n)
    s.text(4 + i, 19 - len(c), c)
s.put(6, 1, "*")
s.box(14, 0, 17, 19)
s.text(15, 1, "Ataque que nunca")
s.text(16, 1, "deja a 0 PV·")
screens.append(s)

# ================================================================== COCINA
s = S("cocina", ["ui", "uimenu"],
      "COCINA (M1b): camp, inn kitchen and Tomasa's house. Top box rows 0-5, tab 'Cocina': 3 slots",
      "rows 1-3 (MARK_CAUGHT = filled / MARK_SEEN = empty col 1, ingredient name cols 3-16, '-'",
      "when empty); row 4: ARROW_RIGHT + the recipe these slots make if it is KNOWN, '???' if not",
      "known, blank when empty. List box rows 6-13, tab 'Ingredientes': cursor col 1, name cols 2-15,",
      "count cols 17-18 (count already minus what is in the slots). A: put in the next slot. B:",
      "take the last slot out (empty slots: leave). Start: cook (quantity box if > 1 possible).",
      "Select: Recetas. Hints box rows 14-17 (rows 15 and 16).")
s.box(0, 0, 5, 19, tab="Cocina")
s.put(1, 1, "●")
s.text(1, 3, "Carne cangrejo")
s.put(2, 1, "●")
s.text(2, 3, "Sal")
s.put(3, 1, "○")
s.text(3, 3, "-")
s.put(4, 1, "▶")
s.text(4, 3, "Cangrejo y sal")
s.box(6, 0, 13, 19, tab="Ingredientes")
for i, (n, c) in enumerate((("Carne cangrejo", "1"), ("Bayas", "5"), ("Sal", "2"), ("Huevas erizo", "1"),
                            ("Pan", "1"), ("Algas", "3"))):
    s.text(7 + i, 2, n)
    s.text(7 + i, 19 - len(c), c)
s.put(7, 1, "*")
s.put(13, 17, "▼")
s.box(14, 0, 17, 19)
s.text(15, 1, "Select")
s.text(15, 9, "Recetas")
s.text(16, 1, "Start")
s.text(16, 9, "Cocinar")
screens.append(s)

s = S("cocina_plato", ["ui", "uimenu"],
      "COCINA result (M1b): BG popup cols 2-17 rows 3-12 over the kitchen. Row 4 '¡Nueva receta!'",
      "only for a new recipe (jingle; blank otherwise), dish icon 16x16 at cols 9-10 rows 6-7",
      "(item icon, $8800), dish name centred row 9 (<= 14), effect row 11 (<= 14). Mejunje:",
      "same box. A: close and redraw the kitchen.")
s.box(0, 0, 5, 19, tab="Cocina")
s.put(1, 1, "○")
s.text(1, 3, "-")
s.put(2, 1, "○")
s.text(2, 3, "-")
s.put(3, 1, "○")
s.text(3, 3, "-")
s.box(6, 0, 13, 19, tab="Ingredientes")
s.box(14, 0, 17, 19)
s.text(15, 1, "Select")
s.text(15, 9, "Recetas")
s.text(16, 1, "Start")
s.text(16, 9, "Cocinar")
s.box(3, 2, 12, 17)
s.text(4, 3, "¡Nueva receta!")
s.text(9, 3, "Cangrejo y sal")
s.text(11, 3, "+25 PV  Coraza")
screens.append(s)

s = S("recetas", ["ui", "uimenu"],
      "RECETAS (M1b, from COCINA with Select): known recipes. Box rows 0-12, tab 'Recetas' + known",
      "count. List rows 1-11 (11 visible): cursor col 1, MARK_CAUGHT col 3 = you have the",
      "ingredients now / MARK_SEEN = missing some, name cols 5-18 (<= 14). Footer rows 13-17: the 1-3",
      "ingredients rows 14-16 (marker col 1 = have it, name cols 3-16, have/need right-aligned",
      "cols 17-18). A: fill the slots with this recipe and go back to COCINA (= 'Repetir receta';",
      "the cursor starts on the last cooked recipe). B: back to COCINA unchanged.")
s.box(0, 0, 12, 19, tab="Recetas  8/32")
for i, (m, n) in enumerate((("●", "Asado simple"), ("○", "Pescado brasa"), ("●", "Cangrejo y sal"),
                            ("○", "Tortilla"), ("●", "Mermelada"), ("○", "Caldo de algas"))):
    s.put(1 + i, 3, m)
    s.text(1 + i, 5, n[:14])
s.put(3, 1, "*")
s.box(13, 0, 17, 19)
s.put(14, 1, "●")
s.text(14, 3, "Carne cangrejo")
s.text(14, 18, "1")
s.put(15, 1, "●")
s.text(15, 3, "Sal")
s.text(15, 18, "2")
screens.append(s)

# ================================================================== TIENDA
def shop(name, mode, items, *hdr):
    s = S(name, ["ui", "uimenu"], *hdr)
    s.box(0, 0, 2, 19)
    s.text(1, 1, mode)
    s.put(1, 13, "$")
    s.text(1, 15, "1250")
    s.box(3, 0, 12, 19)
    for i, (n, c, p) in enumerate(items):
        s.text(4 + 2 * i, 2, n)
        if c:
            s.text(4 + 2 * i, 19 - len(c), c)
        s.put(5 + 2 * i, 14, "$")
        s.text(5 + 2 * i, 19 - len(p), p)
    s.put(4, 1, "*")
    s.put(12, 17, "▼")
    s.box(13, 0, 17, 19)
    return s


s = shop("tienda", "Comprar",
         [("Pocion", "", "20"), ("Farolillo", "", "15"), ("Farolillo fino", "", "40"), ("Red", "", "12")],
         "TIENDA Comprar (M1b). Header row 1: mode cols 1-7, COIN col 13, money right-aligned cols",
         "15-18. List rows 4-11, 2-row pitch (4 visible): name row (cursor col 1, cols 2-15), price row",
         "(COIN + price right-aligned ending col 18). Footer rows 14-16: 2-line description rows 14-15,",
         "'Tienes' + owned count row 16. A: quantity box. B: back to the counter dialogue.")
s.text(14, 1, "Cura 30 PV de una")
s.text(15, 1, "herida·")
s.text(16, 1, "Tienes  3")
screens.append(s)

s = shop("tienda_cantidad", "Comprar",
         [("Pocion", "", "20"), ("Farolillo", "", "15"), ("Farolillo fino", "", "40"), ("Red", "", "12")],
         "TIENDA quantity box (M1b; also MOCHILA Tirar and COCINA x N): BG box cols 8-19 rows 9-11",
         "over the list. 'x' col 10, amount right-aligned cols 11-12, COIN col 14, total",
         "right-aligned cols 15-18 (no coin/total for Tirar/Cocinar). ARROW_UP / ARROW_DOWN on the",
         "borders above/below the amount (col 12). Up/down +-1, left/right +-10, wraps 1 <-> max",
         "(max = what you can afford and carry). A: buy (SFX, 'Gracias!' in the footer). B: cancel.")
s.text(14, 1, "Cura 30 PV de una")
s.text(15, 1, "herida·")
s.text(16, 1, "Tienes  3")
s.put(4, 1, "»")
s.box(9, 8, 11, 19)
s.put(9, 12, "▲")
s.put(11, 12, "▼")
s.text(10, 10, "x")
s.text(10, 12, "3")
s.put(10, 14, "$")
s.text(10, 17, "60")
screens.append(s)

s = shop("tienda_vender", "Vender",
         [("Concha", "x4", "12"), ("Bayas", "x5", "2"), ("Carne cangrejo", "x1", "5"), ("Pocion", "x3", "10")],
         "TIENDA Vender (M1b). Same layout: owned items of all pockets except key items, count",
         "'x' + count right-aligned ending col 18 on the name row (the x tells counts from prices), sell",
         "price (half, materials full) on the price row.")
s.text(14, 1, "Concha de playa·")
s.text(15, 1, "Solo vale dinero·")
screens.append(s)

# ================================================================== CAMP
s = S("campamento", ["ui", "uimenu"],
      "CAMP (M1b), full screen. Rows 0-9: the camp scene picture 20x10 (pixel-artist .pic: Leo,",
      "fire animated 3 frames by tile patches, pot, night; blank here). Status box cols 0-7 rows",
      "10-17: PV row 11, EN row 12, bowl + sac number row 13, lantern + full lanterns row 15, phase",
      "(M2) row 16. Menu box cols 8-19 rows 10-17: 6 entries rows 11-16 (1-row pitch), cursor",
      "col 9, text cols 10-18. Cocinar -> COCINA, Descansar -> ask (dialogue box style in BG),",
      "Salar -> list of perishables (MOCHILA list layout, tab 'Salar'), Capturas -> CAPTURAS,",
      "Guardar -> save box, Recoger -> back to the map (fire disappears). B = Recoger.")
s.box(10, 0, 17, 7)
s.text(11, 1, "PV")
s.text(11, 5, "32")
s.text(12, 1, "EN")
s.text(12, 6, "9")
s.put(13, 1, "Ψ")
s.text(13, 5, "41")
s.put(15, 1, "δ")
s.text(15, 3, "3/12")
s.text(16, 1, "Noche")
s.box(10, 8, 17, 19)
for i, e in enumerate(("Cocinar", "Descansar", "Salar", "Capturas", "Guardar", "Recoger")):
    s.text(11 + i, 10, e)
s.put(11, 9, "*")
screens.append(s)

s = S("capturas", ["ui", "uimenu"],
      "CAPTURAS (M1b, camp): full lanterns (repeated captures). Box rows 0-13, tab 'Capturas' +",
      "count/cap. List rows 1-12: cursor col 1, lantern icon col 2, species name cols 4-13, level",
      "right-aligned cols 16-18 ('Nv' + 1-2 digits). Footer rows 14-17: what 'Cocinar' gives",
      "(rows 15-16). A: popup 'Cocinar / Soltar / Salir' (MOCHILA popup style). B: camp menu.")
s.box(0, 0, 13, 19, tab="Capturas  3/12")
for i, (n, l) in enumerate((("Pinzarro", "Nv3"), ("Dunejo", "Nv4"), ("Pinzarro", "Nv5"))):
    s.put(1 + i, 2, "δ")
    s.text(1 + i, 4, n)
    s.text(1 + i, 19 - len(l), l)
s.put(1, 1, "*")
s.box(14, 0, 17, 19)
s.text(15, 1, "Cocinar da:")
s.text(16, 1, "Carne cangrejo x2")
screens.append(s)

# ================================================================== FAINT, END OF DEMO, OPTIONS, NAME
s = S("desmayo", ["ui"],
      "FAINT (M1b): after 'Leo se desmaya...' in battle, fade to black; this map is loaded with the",
      "LCD off and shown with BGP = 0x1B (inverted: white text on black; the preview shows it",
      "normal). Text typed at 1 char / 4 f, hold 90 f, fade to black, wake up in the clinic map",
      "(script: nurse dialogue + 'Pierdes 150 C').")
s.text(8, 2, "Leo se desmaya···")
screens.append(s)

s = S("opciones", ["ui", "uimenu"],
      "OPCIONES (M1b; from TITLE and the panel). Box rows 2-12, tab 'Opciones'. Rows 4/6/8:",
      "cursor col 2, label cols 3-9, value between ARROW_LEFT col 10 and ARROW_RIGHT col 18 (value",
      "cols 11-17). Texto: Lento / Normal / Rapido (GDD 4.5). Sonido: Estereo / Mono. Left/right",
      "change the value at once (the text-speed sample on rows 14-16 retypes). B / Salir: back.")
s.box(2, 0, 12, 19, tab="Opciones")
s.put(4, 2, "*")
s.text(4, 3, "Texto")
s.put(4, 10, "◀")
s.text(4, 11, "Normal")
s.put(4, 18, "▶")
s.text(6, 3, "Sonido")
s.put(6, 10, "◀")
s.text(6, 11, "Estereo")
s.put(6, 18, "▶")
s.text(8, 3, "Salir")
s.box(13, 0, 17, 19)
s.text(14, 1, "Asi de rapido se")
s.text(16, 1, "salen los textos·")
screens.append(s)

s = S("nombre", ["ui", "uimenu"],
      "NAME (M2): before the intro. Row 2: the name (5 slots cols 8-12, DASH = empty slot), the",
      "next slot blinks 16/16 f. Letter grid box rows 4-14: 9 letters per row at cols 2,4..18, rows",
      "5/7/9 (upper) - Select toggles lower case. Row 12: 'Borrar' (col 3) and 'Fin' (col 14).",
      "Cursor = CURSOR tile left of the letter. B deletes, Start jumps to Fin.")
s.box(0, 0, 3, 19, tab="Tu nombre")
s.text(2, 8, "Leo--")
s.box(4, 0, 14, 19)
letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
for k, ch in enumerate(letters):
    s.put(5 + 2 * (k // 9), 2 + 2 * (k % 9), ch)
s.put(5, 1, "*")
s.text(12, 3, "Borrar")
s.text(12, 15, "Fin")
s.box(15, 0, 17, 19)
s.text(16, 1, "Select  abc")
screens.append(s)

# ================================================================== LAMP (ring lights up) + END OF DEMO
s = S("faro_anillo", ["ui"],
      "LAMP (M1b): scripted scene on the Sala de la Lente map (pixel-artist tileset; blank here).",
      "Sequence in ui.md 13: camera on the lens, palette flashes, ring patch, then this dialogue",
      "with the lighthouse as speaker (tab 'Faro'), then the Bruma wall of the region dissolves.",
      "The ring counter is text in the dialogue ('Anillo 1 de 6'), no extra tiles.")
s.box(12, 0, 17, 19, tab="Faro")
s.text(14, 1, "Anillo 1 de 6")
s.text(16, 1, "La luz llega lejos·")
s.put(17, 17, "▼")
screens.append(s)

def title_rows():
    """Rows 0-5 of title.screen (logo + subtitle) with their legend."""
    lines = (OUT / "title.screen").read_text(encoding="utf-8").splitlines()
    leg, grid, sec = {}, [], None
    for ln in lines:
        if ln.startswith("legend:"):
            sec = "l"; continue
        if ln.startswith("grid:"):
            sec = "g"; continue
        if ln.startswith("sprites:"):
            break
        if sec == "l" and ln and not ln.startswith(";"):
            leg[ln[0]] = ln[2:].strip()
        elif sec == "g":
            grid.append(ln)
    return leg, grid

leg, tgrid = title_rows()
s = S("fin_demo", ["ui", "title"],
      "END OF DEMO (M1b): after the anillo 1 scene. LCD-off load; rows 0-5 are the title logo",
      "(same title tiles), box rows 7-16 with the run summary: registered species, hunts, level,",
      "play time (values right-aligned ending col 17). Row 15 'Gracias por jugar'. A: back to",
      "TITLE (the game is saved first, so Continuar resumes at the lighthouse).")
remap = {ch: chr(0x4E00 + k) for k, ch in enumerate(sorted(leg))}   # fresh keys: no clash with icons
for ch, ref in leg.items():
    LEGEND[remap[ch]] = ref
for r in range(6):
    for c in range(20):
        ch = tgrid[r][c]
        s.put(r, c, remap.get(ch, ch))
s.box(7, 1, 16, 18, tab="Fin de la demo")
s.text(9, 3, "Luces")
s.text(9, 14, "5/48")
s.text(10, 3, "Cazas")
s.text(10, 16, "12")
s.text(11, 3, "Nivel")
s.text(11, 17, "8")
s.text(12, 3, "Tiempo")
s.text(12, 14, "0:42")
s.text(14, 3, "Gracias por")
s.text(15, 3, "jugar!")
screens.append(s)

for s in screens:
    s.write()
print("written", len(screens), "missing punctuation:", MISSING_PUNCT)
