// HAPPY VALLEY - the stable and the week (GDD 2.2, 2.5, 2.7, 2.8). Specification: tests/hv_week.py
// (same slots, same RNG calls in the same order; tests/test_week.py compares them week by week).
#pragma bank 255
#include "hv.h"

horse_t hv_horse[HV_SLOTS];
uint8_t hv_week, hv_season;
int32_t hv_money;
uint16_t hv_fame;
training_t hv_train[TRN_COUNT];                 // tables copied to WRAM at the start (read every week)
growth_t hv_growth[CURVE_COUNT];

static uint16_t x16(uint8_t v) {                // v * 16 (SDCC: (uint16_t)u8 << 4 is sometimes 8-bit)
    uint16_t r = v;
    r <<= 4;
    return r;
}

static uint8_t age_q(const horse_t *h) {
    uint8_t a = h->age < 2 ? 2 : h->age > 8 ? 8 : h->age;
    return (&hv_growth[h->curve].a2)[a - 2];
}

void game_new(void) BANKED {
    uint8_t k;
    start_t s;
    horse_t *h;
    bank_memcpy(BANK(tbl_training), hv_train, tbl_training, sizeof(hv_train));
    bank_memcpy(BANK(tbl_growth), hv_growth, tbl_growth, sizeof(hv_growth));
    memset(hv_horse, 0, sizeof(hv_horse));
    hv_week = 1; hv_season = 1; hv_money = RULE(RULE_MONEY0); hv_fame = 0;
    for (k = 0; k < START_COUNT; k++) {
        bank_memcpy(BANK(tbl_start), &s, &tbl_start[k], sizeof(s));
        h = &hv_horse[k];
        h->state = s.state == START_STATE_CUADRA ? HS_STABLE : HS_MARE;
        h->sex = s.sex; h->age = s.age;
        memcpy(h->name, s.name, sizeof(h->name));
        h->a16[0] = x16(s.vel); h->a16[1] = x16(s.res); h->a16[2] = x16(s.rem); h->a16[3] = x16(s.tem);
        h->sal = s.sal;
        h->pot[0] = s.pvel; h->pot[1] = s.pres; h->pot[2] = s.prem; h->pot[3] = s.ptem; h->pot[4] = s.psal;
        h->dpref = s.dpref; h->surf = s.surf; h->style = s.style; h->curve = s.curve; h->rating = s.rating;
    }
}

static void train(horse_t *h) {
    const training_t *t = &hv_train[h->plan];
    uint8_t i, b, fat0 = h->fat, q = age_q(h), p;
    int16_t room, g, f;
    uint16_t cap;
    for (i = 0; i < 4; i++) {
        b = (&t->vel)[i];
        if (!b) continue;
        room = (int16_t)h->pot[i] - (int16_t)(h->a16[i] >> 4);
        if (room <= 0) continue;
        g = ((int16_t)b * (room < 32 ? room : 32)) >> 5;
        g = (g * q) >> 2;
        if (h->fat > R8(RULE_FAT_TRAIN)) g >>= 1;
        if (g > 0) { g += (int16_t)rng_range(5) - 2; if (g < 0) g = 0; }
        cap = x16(h->pot[i]);
        h->a16[i] = h->a16[i] + g > cap ? cap : h->a16[i] + g;
    }
    f = (int16_t)h->fat + t->fat;
    h->fat = f < 0 ? 0 : f > 100 ? 100 : (uint8_t)f;
    if (t->risk) {
        p = t->risk + (fat0 > R8(RULE_INJ_FAT) ? (fat0 - R8(RULE_INJ_FAT)) >> 1 : 0)
            + (h->sal < R8(RULE_INJ_SAL) ? (R8(RULE_INJ_SAL) - h->sal) >> 3 : 0);
        if (rng_next() < p) {
            h->injury = 3 + rng_range(6);
            if (rng_next() < 32) {
                h->injury = (16 + rng_range(16)) | 0x80;
                h->pot[0] = h->pot[0] > 13 ? h->pot[0] - 3 : 10;
                cap = x16(h->pot[0]);
                if (h->a16[0] > cap) h->a16[0] = cap;
            }
        }
    }
}

void week_advance(void) BANKED {
    uint8_t k, i, worked[HV_SLOTS], rec, stable = 0, farm = 0, q;
    uint16_t lo, cap;
    horse_t *h;
    for (k = 0, h = hv_horse; k < HV_SLOTS; k++, h++) {         // 2. training
        worked[k] = 0;
        if (h->state == HS_STABLE && !h->injury) { train(h); worked[k] = h->plan != TRN_DESCANSO; }
    }
    for (k = 0, h = hv_horse; k < HV_SLOTS; k++, h++) {         // 4. recovery, injuries, idle, growth
        if (h->state == HS_MARE || h->state == HS_FOAL) farm++;
        if (h->state != HS_STABLE) continue;
        stable++;
        rec = R8(RULE_REC_BASE) + (h->sal >> 3);
        h->fat = h->fat > rec ? h->fat - rec : 0;
        if (h->injury) {
            i = (h->injury & 0x7F) - 1;
            h->injury = i ? (i | (h->injury & 0x80)) : 0;
        }
        h->idle = worked[k] ? 0 : (h->idle < 255 ? h->idle + 1 : 255);
        q = age_q(h);
        for (i = 0; i < 3; i++) {
            if (h->idle >= R8(RULE_IDLE_WEEKS)) {
                lo = x16(h->pot[i]) >> 1;
                h->a16[i] = h->a16[i] > lo + R8(RULE_IDLE_LOSS) ? h->a16[i] - R8(RULE_IDLE_LOSS) : lo;
                if (h->a16[i] < lo) h->a16[i] = lo;
            }
            if (h->age >= 2 && h->age <= 4) {
                cap = x16(h->pot[i]);
                h->a16[i] = h->a16[i] + q > cap ? cap : h->a16[i] + q;
            }
        }
    }
    hv_money -= (int32_t)(RULE(RULE_BOX_COST) * stable + RULE(RULE_FARM_COST) * farm);   // 5.
    if (++hv_week > R8(RULE_WEEKS)) { hv_week = 1; hv_season++; }                         // 6.
}
