/* sbheadless: run a Game Boy ROM headless in the SameBoy core, driven by a plan file.
 *
 * Built by harness/sbrun.py (see build_driver) against tools/sameboy/src/SameBoy-<ver>/Core; sbrun.py writes the
 * plan, runs this program and evaluates checks from its stdout. Not meant to be called by hand.
 *
 * Usage: sbheadless ROM BOOTROM PLAN OUTDIR FRAMES MODEL(dmg|cgb|sgb) RAM(zeros|ones|random) COUNT_BOOT(0|1)
 *
 * Plan lines (frame F counts from 1; with COUNT_BOOT=0 frame 1 is the first whole frame after the boot ROM unmaps):
 *   K F MASK              joypad mask (bit order of GB_key_t) held from frame F on
 *   S F                   write OUTDIR/shot_FFFF.rgb (160x144 RGB) at the end of frame F
 *   R F MEM ADDR LEN      print "R F MEM ADDR hex" at the end of frame F
 *   D F MEM START LEN NAME   write OUTDIR/NAME.bin (LEN -1 = to the end of the region)
 *   I sram PATH|-         cartridge RAM before frame 1: all 0xFF, then PATH's bytes
 *   O sram PATH           write the whole cartridge RAM at the last frame
 * MEM = bus wram vram oam hram sram rom. Final line: "END frames boot_frames sram_size AF BC DE HL SP PC" (hex).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "Core/gb.h"

typedef struct { int kind, frame; char mem[8]; long addr, len; char path[1024]; unsigned mask; } cmd_t;

static uint32_t pixels[256 * 224];
static volatile int vblank_seen;
static cmd_t *cmds;
static int ncmds;

static uint32_t rgb_encode(GB_gameboy_t *gb, uint8_t r, uint8_t g, uint8_t b)
{
    (void)gb;
    return ((uint32_t)r << 16) | ((uint32_t)g << 8) | b;
}

static void on_vblank(GB_gameboy_t *gb, GB_vblank_type_t type)
{
    (void)gb; (void)type;
    vblank_seen = 1;
}

static void quiet_log(GB_gameboy_t *gb, const char *s, GB_log_attributes_t a)
{
    (void)gb; (void)s; (void)a;
}

static uint8_t *region(GB_gameboy_t *gb, const char *mem, size_t *size)
{
    GB_direct_access_t t;
    uint16_t bank;
    if (!strcmp(mem, "wram")) t = GB_DIRECT_ACCESS_RAM;
    else if (!strcmp(mem, "vram")) t = GB_DIRECT_ACCESS_VRAM;
    else if (!strcmp(mem, "oam")) t = GB_DIRECT_ACCESS_OAM;
    else if (!strcmp(mem, "hram")) t = GB_DIRECT_ACCESS_HRAM;
    else if (!strcmp(mem, "sram")) t = GB_DIRECT_ACCESS_CART_RAM;
    else if (!strcmp(mem, "rom")) t = GB_DIRECT_ACCESS_ROM;
    else { *size = 0; return NULL; }
    return GB_get_direct_access(gb, t, size, &bank);
}

static int read_byte(GB_gameboy_t *gb, const char *mem, long addr)
{
    size_t size;
    uint8_t *p;
    if (!strcmp(mem, "bus")) return GB_safe_read_memory(gb, (uint16_t)addr);
    p = region(gb, mem, &size);
    return (p && addr >= 0 && (size_t)addr < size) ? p[addr] : -1;
}

static void write_file(const char *dir, const char *name, const void *data, size_t n)
{
    char path[1200];
    FILE *f;
    snprintf(path, sizeof path, "%s/%s", dir, name);
    f = fopen(path, "wb");
    if (!f) { fprintf(stderr, "cannot write %s\n", path); exit(2); }
    fwrite(data, 1, n, f);
    fclose(f);
}

static void load_plan(const char *path)
{
    char line[1400];
    FILE *f = fopen(path, "r");
    if (!f) { fprintf(stderr, "cannot read plan %s\n", path); exit(2); }
    cmds = calloc(200000, sizeof *cmds);
    while (fgets(line, sizeof line, f) && ncmds < 200000) {
        cmd_t *c = &cmds[ncmds];
        line[strcspn(line, "\r\n")] = 0;
        if (line[0] == 'K' && sscanf(line + 1, "%d %u", &c->frame, &c->mask) == 2) c->kind = 'K';
        else if (line[0] == 'S' && sscanf(line + 1, "%d", &c->frame) == 1) c->kind = 'S';
        else if (line[0] == 'R' && sscanf(line + 1, "%d %7s %li %li", &c->frame, c->mem, &c->addr, &c->len) == 4) c->kind = 'R';
        else if (line[0] == 'D' && sscanf(line + 1, "%d %7s %li %li %1023s", &c->frame, c->mem, &c->addr, &c->len, c->path) == 5) c->kind = 'D';
        else if ((line[0] == 'I' || line[0] == 'O') && sscanf(line + 1, "%7s %1023[^\n]", c->mem, c->path) == 2) c->kind = line[0];
        else continue;
        ncmds++;
    }
    fclose(f);
}

static void end_of_frame(GB_gameboy_t *gb, int frame, const char *out)
{
    for (int i = 0; i < ncmds; i++) {
        cmd_t *c = &cmds[i];
        if (c->frame != frame) continue;
        if (c->kind == 'S') {
            static uint8_t rgb[160 * 144 * 3];
            char name[32];
            for (int p = 0; p < 160 * 144; p++) {
                rgb[p * 3] = pixels[p] >> 16; rgb[p * 3 + 1] = pixels[p] >> 8; rgb[p * 3 + 2] = pixels[p];
            }
            snprintf(name, sizeof name, "shot_%04d.rgb", frame);
            write_file(out, name, rgb, sizeof rgb);
        }
        else if (c->kind == 'R') {
            printf("R %d %s %ld ", frame, c->mem, c->addr);
            for (long k = 0; k < c->len; k++) {
                int v = read_byte(gb, c->mem, c->addr + k);
                printf(v < 0 ? "--" : "%02x", v);
            }
            printf("\n");
        }
        else if (c->kind == 'D') {
            size_t size = 0x10000;
            uint8_t *p = NULL, *buf;
            char name[1100];
            if (strcmp(c->mem, "bus")) p = region(gb, c->mem, &size);
            if (c->addr < 0 || (size_t)c->addr > size) continue;
            long n = c->len < 0 ? (long)size - c->addr : c->len;
            if ((size_t)(c->addr + n) > size) n = (long)size - c->addr;
            buf = malloc(n ? n : 1);
            for (long k = 0; k < n; k++) buf[k] = p ? p[c->addr + k] : GB_safe_read_memory(gb, (uint16_t)(c->addr + k));
            snprintf(name, sizeof name, "%s.bin", c->path);
            write_file(out, name, buf, n);
            free(buf);
        }
    }
}

int main(int argc, char **argv)
{
    static GB_gameboy_t gb;
    if (argc != 9) {
        fprintf(stderr, "usage: sbheadless ROM BOOTROM PLAN OUTDIR FRAMES MODEL RAM COUNT_BOOT\n");
        return 3;
    }
    const char *rom = argv[1], *boot = argv[2], *out = argv[4], *model = argv[6], *ram = argv[7];
    int frames = atoi(argv[5]), count_boot = atoi(argv[8]);
    GB_model_t m = !strcmp(model, "cgb") ? GB_MODEL_CGB_E : !strcmp(model, "sgb") ? GB_MODEL_SGB_NTSC : GB_MODEL_DMG_B;

    load_plan(argv[3]);
    GB_random_seed(0x5EED);                   /* deterministic power-on noise unless --ram random asks otherwise */
    if (!strcmp(ram, "random")) GB_random_seed((uint64_t)time(NULL));
    GB_init(&gb, m);
    if (GB_load_boot_rom(&gb, boot)) { fprintf(stderr, "cannot load boot ROM %s\n", boot); return 2; }
    if (GB_load_rom(&gb, rom)) { fprintf(stderr, "cannot load ROM %s\n", rom); return 2; }
    GB_reset(&gb);
    GB_set_vblank_callback(&gb, on_vblank);
    GB_set_pixels_output(&gb, pixels);
    GB_set_rgb_encode_callback(&gb, rgb_encode);
    GB_set_palette(&gb, &GB_PALETTE_GREY);
    GB_set_color_correction_mode(&gb, GB_COLOR_CORRECTION_DISABLED);
    GB_set_log_callback(&gb, quiet_log);
    GB_set_emulate_joypad_bouncing(&gb, false);
    GB_set_rtc_mode(&gb, GB_RTC_MODE_ACCURATE);
    GB_set_turbo_mode(&gb, true, true);       /* no real-time sleep (timing.c), but render every frame */

    if (strcmp(ram, "random")) {              /* zeros / ones: WRAM and HRAM; the boot ROM clears VRAM itself */
        int fill = !strcmp(ram, "ones") ? 0xFF : 0x00;
        size_t size; uint8_t *p;
        if ((p = region(&gb, "wram", &size))) memset(p, fill, size);
        if ((p = region(&gb, "hram", &size))) memset(p, fill, size);
    }
    for (int i = 0; i < ncmds; i++) {
        if (cmds[i].kind != 'I') continue;
        size_t size; uint8_t *p = region(&gb, "sram", &size);
        if (!p) continue;
        memset(p, 0xFF, size);
        if (strcmp(cmds[i].path, "-")) {
            FILE *f = fopen(cmds[i].path, "rb");
            if (f) { fread(p, 1, size, f); fclose(f); }
        }
    }

    int frame = 0, boot_frames = 0, booted = 0;
    unsigned mask = 0;
    while (frame < frames) {
        if (booted || count_boot) {
            for (int i = 0; i < ncmds; i++)
                if (cmds[i].kind == 'K' && cmds[i].frame == frame + 1) mask = cmds[i].mask;
            GB_set_key_mask(&gb, (GB_key_mask_t)mask);
        }
        vblank_seen = 0;
        while (!vblank_seen) GB_run(&gb);
        if (!booted) {                        /* frames count from the end of the boot ROM, as gbrun and PyBoy */
            boot_frames++;
            if (gb.boot_rom_finished) booted = 1;
            if (!count_boot) continue;
        }
        frame++;
        end_of_frame(&gb, frame, out);
    }
    for (int i = 0; i < ncmds; i++) {
        if (cmds[i].kind != 'O') continue;
        size_t size; uint8_t *p = region(&gb, "sram", &size);
        FILE *f = fopen(cmds[i].path, "wb");
        if (f) { if (p) fwrite(p, 1, size, f); fclose(f); }
    }
    size_t sram_size = 0;
    region(&gb, "sram", &sram_size);
    printf("END %d %d %zu", frame, boot_frames, sram_size);
    for (int r = 0; r < GB_REGISTERS_16_BIT; r++) printf(" %04x", gb.registers[r]);
    printf("\n");
    GB_free(&gb);
    return 0;
}
