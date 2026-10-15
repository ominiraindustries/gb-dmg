// HAPPY VALLEY - management screens, greybox (GDD 4): ESTABLO (date, money, the stable's horses, cursor),
// FICHA (one horse: attributes with bars, stars, fatigue, injury, distance, surface, style and the week's
// plan, changed with left/right), INFORME (the week's report: attribute changes, injuries, expenses).
// Text is proportional (gbe_vwf) drawn into the text slot with the LCD off by ui_text(); a screen uses
// at most VRAM_TEXT_COUNT tiles (ui_next). The plan names are drawn once per FICHA and swapped by map
// index through gbe_vq when the plan changes.
#pragma bank 255
#include "hv.h"
#include "greybox.h"
#include "font_mini.h"

#define T(n)        (VRAM_GREYBOX + GREYBOX_##n)
#define MAP(r, c)   ((uint8_t *)0x9800 + gbe_row32(r) + (c))
#define PLAN_W      7                           // tiles per plan name ("Descanso")
#define STRIP_MAX   20

uint8_t ui_next;                                // next free tile of the text slot (tests: <= 200)
uint8_t ui_sel, ui_n, ui_slot[HV_SLOTS];        // ESTABLO: cursor, rows, the horse slot of each row
uint8_t ui_plan0;                               // FICHA: first tile of the plan names
static uint8_t strip[STRIP_MAX * 16];
static uint16_t rep_a16[HV_SLOTS][4];
static uint8_t rep_inj[HV_SLOTS];
static int32_t rep_money;
static char line[32];

// ---------------------------------------------------------------- text helpers (LCD off)
static void ui_text(uint8_t row, uint8_t col, const char *s) {
    uint8_t n = (vwf_width(s) + 9) >> 3, k;
    if (n > STRIP_MAX) n = STRIP_MAX;
    if (n > 20 - col) n = 20 - col;
    if (ui_next + n > VRAM_TEXT_COUNT) return;  // out of slot: tests check ui_next
    vwf_clear(strip, n);
    vwf_draw(strip, n, 1, s);
    set_bkg_data(VRAM_TEXT + ui_next, n, strip);
    for (k = 0; k < n; k++) *MAP(row, col + k) = VRAM_TEXT + ui_next + k;
    ui_next += n;
}

static char *put_s(char *d, const char *s) { while (*s) *d++ = *s++; *d = 0; return d; }

static char *put_n(char *d, int32_t v) {        // decimal, with a minus sign
    char b[11];
    uint8_t n = 0;
    uint32_t u;
    if (v < 0) { *d++ = '-'; u = (uint32_t)-v; } else u = (uint32_t)v;
    do { b[n++] = '0' + (uint8_t)(u % 10); u /= 10; } while (u);
    while (n) *d++ = b[--n];
    *d = 0;
    return d;
}

static void clear_map(void) {
    uint8_t r;
    for (r = 0; r < 18; r++) memset(MAP(r, 0), T(BLANK), 20);
}

static uint8_t points(const horse_t *h, uint8_t i) {   // attribute in points (SAL is direct)
    return i < 4 ? (uint8_t)(h->a16[i] >> 4) : h->sal;
}

static uint8_t stars(const horse_t *h) {        // GDD 2.1: mean of the VEL RES REM ceilings
    uint8_t m = (uint8_t)(((uint16_t)h->pot[0] + h->pot[1] + h->pot[2]) * 85 >> 8);
    return m < 40 ? 1 : m < 55 ? 2 : m < 70 ? 3 : m < 85 ? 4 : 5;
}

static const char *const plan_name[TRN_COUNT] = { "Descanso", "Galope", "Series", "Fondo", "Remates", "Salidas" };
static const char *const attr_name[5] = { "Vel", "Res", "Rem", "Tem", "Sal" };
static const char *const style_name[3] = { "Puntero", "Acecho", "Cerrador" };

static uint8_t cls_of(uint8_t rating) {         // GDD 2.3: C5 0-39 ... C1 100+
    return rating >= 100 ? 1 : rating >= 80 ? 2 : rating >= 60 ? 3 : rating >= 40 ? 4 : 5;
}

// ---------------------------------------------------------------- ESTABLO
static void stable_build(void) {
    uint8_t k, row = 3;
    horse_t *h;
    char *d;
    d = put_s(line, "Semana "); d = put_n(d, hv_week); d = put_s(d, "   Temporada "); put_n(d, hv_season);
    ui_text(0, 1, line);
    d = put_s(line, "Dinero "); d = put_n(d, hv_money); d = put_s(d, "k   Fama "); put_n(d, hv_fame);
    ui_text(1, 1, line);
    ui_n = 0;
    for (k = 0, h = hv_horse; k < HV_SLOTS; k++, h++) {
        if (h->state != HS_STABLE) continue;
        ui_slot[ui_n++] = k;
        ui_text(row, 1, h->name);
        d = put_s(line, "C"); d = put_n(d, cls_of(h->rating)); d = put_s(d, " "); put_n(d, h->rating);
        ui_text(row, 14, line);
        if (h->injury) { d = put_s(line, "Lesion "); d = put_n(d, h->injury & 0x7F); put_s(d, " sem"); }
        else { d = put_s(line, plan_name[h->plan]); }
        ui_text(row + 1, 2, line);
        d = put_s(line, "Fat "); put_n(d, h->fat);
        ui_text(row + 1, 14, line);
        row += 2;
    }
    for (k = 0, h = hv_horse; k < HV_SLOTS; k++, h++)
        if (h->state == HS_MARE) { d = put_s(line, "Granja: "); put_s(d, h->name); ui_text(row + 1, 1, line); break; }
    ui_text(16, 1, "A ficha   Start semana");
    ui_text(17, 1, "Select carrera de prueba");
    if (ui_sel >= ui_n) ui_sel = 0;
    menu_open(ui_n, ui_sel, 0, MAP(3, 0), 64, T(ARROW_R), T(BLANK));
}

// ---------------------------------------------------------------- FICHA
static void bar(uint8_t row, uint8_t col, uint8_t v) {
    uint8_t n = (uint8_t)(((uint16_t)v * 5 + 31) >> 6), k;     // 0-99 -> 0-8 tiles
    for (k = 0; k < 8; k++) *MAP(row, col + k) = k < n ? T(SOLID) : T(FLOOR);
}

static void plan_show(const horse_t *h) {       // the map row of the plan: the chosen name's tiles
    uint8_t t[PLAN_W], k;
    for (k = 0; k < PLAN_W; k++) t[k] = ui_plan0 + h->plan * PLAN_W + k;
    vq_push(MAP(15, 8), t, PLAN_W);
}

static void horse_build(void) {
    horse_t *h = &hv_horse[ui_slot[ui_sel]];
    uint8_t i, k;
    char *d;
    ui_text(0, 1, h->name);
    d = put_s(line, h->sex ? "Hembra, " : "Macho, "); d = put_n(d, h->age); d = put_s(d, " anos   C");
    d = put_n(d, cls_of(h->rating)); d = put_s(d, " "); put_n(d, h->rating);
    ui_text(1, 1, line);
    for (i = 0; i < 5; i++) {
        ui_text(3 + i, 1, attr_name[i]);
        d = line; put_n(d, points(h, i));
        ui_text(3 + i, 4, line);
        bar(3 + i, 7, points(h, i));
    }
    ui_text(9, 1, "Potencial");
    for (k = stars(h), i = 0; i < k; i++) *MAP(9, 10 + (i << 1)) = T(CHECK);
    d = put_s(line, "Fatiga "); put_n(d, h->fat);
    ui_text(10, 1, line);
    if (h->injury) { d = put_s(line, "Lesion "); d = put_n(d, h->injury & 0x7F); put_s(d, h->injury & 0x80 ? " sem (grave)" : " sem"); }
    else put_s(line, "Sano");
    ui_text(10, 10, line);
    d = put_s(line, "Distancia "); d = put_n(d, h->dpref); put_s(d, "00 m");
    ui_text(11, 1, line);
    d = put_s(line, h->surf >= 0 ? "Cesped +" : "Arena +"); put_n(d, h->surf >= 0 ? h->surf : -h->surf);
    ui_text(12, 1, line);
    ui_text(12, 10, style_name[h->style]);
    ui_text(15, 1, "Plan");
    *MAP(15, 7) = T(ARROW_R);
    ui_plan0 = VRAM_TEXT + ui_next;
    for (i = 0; i < TRN_COUNT; i++) {           // the 6 names, PLAN_W tiles each (only one on the map)
        vwf_clear(strip, PLAN_W);
        vwf_draw(strip, PLAN_W, 1, plan_name[i]);
        set_bkg_data(VRAM_TEXT + ui_next, PLAN_W, strip);
        ui_next += PLAN_W;
    }
    for (k = 0; k < PLAN_W; k++) *MAP(15, 8 + k) = ui_plan0 + h->plan * PLAN_W + k;
    ui_text(17, 1, "Izq/Der plan   B volver");
}

// ---------------------------------------------------------------- INFORME
void report_snapshot(void) BANKED {             // before week_advance()
    uint8_t k, i;
    for (k = 0; k < HV_SLOTS; k++) {
        for (i = 0; i < 4; i++) rep_a16[k][i] = hv_horse[k].a16[i];
        rep_inj[k] = hv_horse[k].injury;
    }
    rep_money = hv_money;
}

// the week's change of one attribute in tenths of a point (the week moves 1/16ths: "Vel +0.6")
static char *put_delta(char *d, uint8_t i, int16_t d16) {
    uint8_t t;
    d = put_s(d, attr_name[i]);
    d = put_s(d, d16 < 0 ? " -" : " ");        // the font has no +
    if (d16 < 0) d16 = -d16;
    t = (uint8_t)((d16 * 10 + 8) >> 4);
    d = put_n(d, t / 10); d = put_s(d, "."); d = put_n(d, t % 10);
    return put_s(d, "  ");
}

static void report_build(void) {
    uint8_t k, i, row = 2, n;
    int16_t d16;
    horse_t *h;
    char *d;
    d = put_s(line, "Parte de la semana "); put_n(d, hv_week);
    ui_text(0, 1, line);
    for (k = 0, h = hv_horse; k < HV_SLOTS && row < 14; k++, h++) {
        if (h->state != HS_STABLE) continue;
        ui_text(row++, 1, h->name);
        d = line; *d = 0;
        if (h->injury && !rep_inj[k]) { d = put_s(d, "Se lesiona: "); d = put_n(d, h->injury & 0x7F); put_s(d, " semanas"); }
        else for (i = 0, n = 0; i < 4 && n < 3; i++) {   // the changed ones, 3 at most (fits 20 tiles)
            d16 = (int16_t)h->a16[i] - (int16_t)rep_a16[k][i];
            if (d16) { d = put_delta(d, i, d16); n++; }
        }
        if (!line[0]) put_s(line, h->injury ? "Lesionado" : "Sin cambios");
        ui_text(row++, 2, line);
    }
    d = put_s(line, "Gastos "); d = put_n(d, hv_money - rep_money); put_s(d, "k");
    ui_text(14, 1, line);
    d = put_s(line, "Dinero "); d = put_n(d, hv_money); put_s(d, "k");
    ui_text(15, 1, line);
    ui_text(17, 1, "A continuar");
}

// ---------------------------------------------------------------- build and update
void ui_build(uint8_t which) BANKED {
    ui_next = 0;
    clear_map();
    if (which == SC_STABLE) stable_build();
    else if (which == SC_HORSE) horse_build();
    else report_build();
}

// returns the next screen (0xFF = stay)
uint8_t ui_update(uint8_t which) BANKED {
    uint8_t m;
    horse_t *h;
    if (which == SC_STABLE) {
        if (pressed & J_START) { report_snapshot(); week_advance(); return SC_REPORT; }
        if (pressed & J_SELECT) return SC_MENU;
        m = menu_update();
        if (m < MENU_BACK) { ui_sel = m; return SC_HORSE; }
    } else if (which == SC_HORSE) {
        h = &hv_horse[ui_slot[ui_sel]];
        if (pressed & (J_LEFT | J_RIGHT)) {
            if (pressed & J_LEFT) h->plan = h->plan ? h->plan - 1 : TRN_COUNT - 1;
            else h->plan = h->plan + 1 < TRN_COUNT ? h->plan + 1 : 0;
            plan_show(h);
            sfx(0);
        }
        if (pressed & J_B) return SC_STABLE;
    } else if (pressed & (J_A | J_START)) return SC_STABLE;
    return 0xFF;
}
