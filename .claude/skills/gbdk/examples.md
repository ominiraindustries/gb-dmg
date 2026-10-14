# GBDK 4.5.0 example programs index

Root: `tools/gbdk/examples/`. Descriptions from `docs/pages/07_sample_programs.md`, each
example's Readme and a skim of its source. `cross-platform/*` examples build for GB too (use the
`#if defined(GAMEBOY)` / `NINTENDO` branches; ignore SMS/GG/NES code) and are often the better
reference. Makefiles show the exact lcc/png2asset flags used.

## Read-first list for our games
| Technique | Example |
|---|---|
| Minimal project / main loop | `gb/template_minimal/main.c`, `gb/template_subfolders` |
| Metasprites, animation, flipping, hiwater + `hide_sprites_range` | `cross-platform/metasprites` |
| Sub-pixel (fixed point) movement with velocity | `cross-platform/simple_physics/src/phys.c` |
| Complete small game: tiles, metasprites, levels, camera, collision | `cross-platform/platformer_template` |
| Scrolling a map larger than 32x32 (`set_bkg_submap` column/row streaming) | `cross-platform/large_map` |
| Text with your own font tiles; typewriter; dialogue boxes | `cross-platform/text_basic`, `text_typewriter`, `text_advanced_dialogue` |
| Button edge detection macros, joypad test | `cross-platform/joytest`, `metasprites` (`KEY_PRESSED`) |
| Interrupt handlers (VBL + TIM), `CRITICAL` access to shared counters | `cross-platform/irq` |
| LCD/STAT per-scanline effect via `add_LCD` + `nowait_int_handler` | `gb/lcd_isr_wobble` |
| Same effect with raw `ISR_VECTOR` (no dispatcher), `INCBIN` graphics | `gb/isr_vector` |
| Sound registers playground (find SFX values) | `gb/sound` (Readme lists keys) |
| ROM banking basics / autobank / far pointers / nonintrinsic | `cross-platform/banks`, `banks_autobank`, `banks_farptr`, `banks_nonintrinsic` |
| SRAM variables via `#pragma dataseg DATA_N` | `cross-platform/sram_banks` |
| HRAM variables (`SFR`) | `gb/hram` |
| Random numbers, fast range reduction, distributions | `gb/rand`, `cross-platform/randtest` |
| BCD scores | `cross-platform/bcd` |
| Emulator logging/profiling (`EMU_printf`, `EMU_PROFILE_*`) | `cross-platform/emu_debug` |
| Crash dump screen | `gb/crash` |
| Compressed tiles (gbcompress) / RLE maps | `cross-platform/gbdecompress`, `cross-platform/rle_map` |
| Binary includes | `cross-platform/incbin` |

## gb/ (Game Boy specific)
| Path | Demonstrates |
|---|---|
| `gb/apa_image` | APA (bitmap) mode via `drawing.h` to show a 160x144 image with > 256 tiles; LCD ISRs installed automatically |
| `gb/colorbar` | CGB color palettes (not DMG) |
| `gb/comm` | serial link `send_byte`/`receive_byte` |
| `gb/crash` | `#include <gb/crash_handler.h>` crash dump on RST 38 |
| `gb/dscan` | "Deep Scan" full small game (CGB-aware), sprites/bg/window, old GBTD/GBMB assets |
| `gb/filltest` | `drawing.h` primitives (lines, boxes, circles): slow, not for games |
| `gb/galaxy` | C translation of `space.s`: sprites, window, bg scrolling, fixed point |
| `gb/gb-dtmf` | DTMF tone generator (sound + UI) |
| `gb/gbtype` | detect DMG / MGB / SGB / CGB / GBA (`_cpu`, `sgb_check`), `-Wm-ys` |
| `gb/hblank_copy` | `hblank_copy_vram()` (`gb/hblankcpy.h`): fast VRAM copy during HBlanks with LCD on |
| `gb/hicolor` | CGB hi-color images (`png2hicolorgb`): not DMG |
| `gb/hram` | `SFR` variable in HRAM |
| `gb/isr_vector` | `ISR_VECTOR(VECTOR_STAT, f)` with `CRITICAL INTERRUPT` handler |
| `gb/lcd_isr_wobble` | `add_LCD` + `STATF_MODE00` HBlank interrupt changing `SCX_REG` per line |
| `gb/linkerfile` | passing objects through a `.lk` linkerfile (`-Wl-f`), long command lines |
| `gb/mbc3_rtc` | MBC3 real-time clock |
| `gb/mbc5_rumble` | MBC5 rumble (cart types 0x1C-0x1E) |
| `gb/mbc7_accelerometer` | MBC7 tilt sensor (don't `vsync()` for 1.2 ms after latching) |
| `gb/paint` | painting program with `drawing.h`, big sprites |
| `gb/ram_function` | copying a function to WRAM/HRAM and calling it (`-Wl-g` address binding) |
| `gb/rand` | `initrand`/`rand`/`arand`, `RAND_RANGE_8BIT` fast modulo |
| `gb/rpn` | RPN calculator (stdio text input) |
| `gb/sgb_border` | SGB border with png2asset (`-map -bpp 4 -max_palettes 4 -pack_mode sgb -use_map_attributes`) |
| `gb/sgb_pong`, `gb/sgb_sfx` | SGB multiplayer / SGB sound effects |
| `gb/sound` | interactive sound register editor, register dump |
| `gb/space` | pure assembly program (sdasgb syntax reference) |
| `gb/template_minimal` | smallest Makefile project |
| `gb/template_subfolders` | src/ + res/ layout Makefile |
| `gb/wav_sample` | playing 4-bit PCM samples through channel 3, samples in banks |

## cross-platform/ (all build for GB)
| Path | Demonstrates |
|---|---|
| `banks` | fixed banks via filename flags (`bank.ba0.bo2.c` -> `-Wf-bo2 -Wf-ba0`), SRAM banks |
| `banks_autobank` | `#pragma bank 255`, `BANKREF`/`BANKREF_EXTERN`/`BANK`, `BANKED`, `NONBANKED`, mixing fixed + auto banks |
| `banks_farptr` | `TO_FAR_PTR`, `FAR_CALL` |
| `banks_nonintrinsic` | `__addressmod` so the compiler switches ROM/SRAM banks automatically when banked data is accessed |
| `bcd` | `uint2bcd`, `bcd_add`, `bcd2text` |
| `display_system` | `get_system()` 50/60 Hz handling |
| `emu_debug` | `EMU_printf`, `EMU_MESSAGE`, profiling macros |
| `fonts` | built-in font system (`font_load`, `font_set`, `mode`) |
| `gbdecompress` | gbcompress'd tiles -> `gb_decompress_bkg_data` |
| `gbprinter` | Game Boy Printer output |
| `incbin` | `INCBIN` + `INCBIN_SIZE` + `BANK` |
| `irq` | `add_VBL`, `add_TIM`, `set_interrupts`, `CRITICAL` |
| `joytest` | joypad reading, multi-pad (`joypad_init`/`joypad_ex`) |
| `large_map` | big map streaming with `set_bkg_submap`, camera clamping |
| `libc_memcpy`, `libc_string` | C library string/memory functions |
| `logo` | full-screen logo from png2asset `-map` with `.meta` arg files |
| `metasprites` | png2asset metasprites, `move_metasprite_ex/flipx/flipy/flipxy`, hiwater hiding |
| `multiplayer` | up to 4 pads via `joypad_init(4, &joypads)` / `joypad_ex` (SGB multitap) |
| `platformer_template` | game structure (camera.c, level.c, player.c), tileset + `-source_tileset` level maps |
| `pong` | tiny complete game |
| `randtest` | random generator test |
| `rle_map` | RLE-compressed map decoded column by column while scrolling |
| `scroller` | text scroller using an LYC `add_LCD` handler |
| `simple_physics` | 12.4 fixed point position/velocity, gravity-like accel |
| `sram_banks` | `#pragma dataseg DATA_0/1`, `ENABLE_RAM`, `SWITCH_RAM` |
| `text_basic`, `text_typewriter`, `text_advanced_dialogue` | font PNG via png2asset `-map -keep_palette_order -noflip`, char->tile mapping, `set_vram_byte` drawing |

Note: example Makefiles use `-Wl-yt0x1B`; lcc forwards it to makebin exactly like `-Wm-yt0x1B`.
