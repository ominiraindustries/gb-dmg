# Game feel: starting numbers (59.73 fps, pixels)

Starting points from common practice in commercial GB/NES-era games. Every value is a
parameter in a table or `#define`, tuned by the user in playtest. Use 8.8 fixed point for
sub-pixel speeds (`uint16_t`, 0x0100 = 1 px/frame).

**Verify, don't estimate:** add the values to `harness/physics.py` (`GAMES`) and run
`python harness/physics.py --game <game>`: exact 8.8 simulation of the frame order the games use,
giving height, air time, distance, climbable blocks and jumpable gaps (matched against the ROM
in games/platformer/tests/test_physics_model.py). Level lints should import it.

## Platformer movement (16x16 hero)
| Parameter | Start value | Notes |
|---|---|---|
| Walk max speed | 1.0-1.5 px/f (0x0100-0x0180) | GB screens are small: slower than NES feels right |
| Run max speed (B held) | 2.0 px/f | optional |
| Acceleration | 0x0018-0x0030 per frame | reaches max in ~6-10 frames |
| Deceleration (no input) | 0x0030-0x0040 per frame | stop faster than you start |
| Turn-around (skid) | 2x deceleration | |
| Gravity | 0x0040 per frame | |
| Jump initial velocity | -0x0380 to -0x0400 | ~3-4 tiles high |
| Variable jump | release A while rising: vy = max(vy, -0x0100) | essential |
| Max fall speed | 0x0300-0x0400 | must be < 8 px/f (tile size) to avoid tunneling |
| Coyote time | 4-6 frames | jump still allowed after leaving a ledge |
| Jump buffer | 4-6 frames | A pressed just before landing still jumps |
| Invulnerability after hit | 60-90 frames, sprite blinks every 4 frames | blink = hide sprite on alternate frames |

## Top-down movement
8-way, 1.0-1.5 px/f, diagonal either same speed per axis (simpler, faster diagonals: acceptable on GB)
or 0.7x per axis via table. Snap-to-grid games: move 1 tile per 8-16 frames.

## Puzzle / falling blocks (measured in games/tetris)
| Parameter | Value |
|---|---|
| DAS delay / repeat | 16 / 6 frames |
| Soft drop | 1 row / 2 frames |
| Lock delay | 30 frames, max 15 resets |
| Line clear animation | 24 frames |
| Gravity table | GB Tetris: 53,49,45,41,37,33,28,22,17,11,10,9,8,7,6,6,5,5,4,4,3 frames/row |

## Shooter
Player 1.5-2 px/f; player bullets 4 px/f, max 3-4 on screen; enemy bullets 1-2 px/f (readable);
auto-fire every 8-12 frames while A held; hitbox smaller than the sprite (e.g. 4x4 core).

## Juice on a DMG (cheap and effective)
- Hit-stop: freeze game logic 2-4 frames on impact.
- Screen shake: offset SCX/SCY by ±1-2 px for 6-10 frames (BG only; move sprites too or they drift).
- Flash: invert BGP for 1-2 frames (`BGP_REG = ~BGP_REG`), use sparingly (LCD ghosting, epilepsy).
- Fades: step BGP through 3-4 palettes over ~16 frames for transitions.
- Squash/stretch: alternate sprite frames on landing/jump.
- Sound on every interaction; distinct pitches for success/failure.
- Particles: 2-4 small sprites max, short life (8-16 frames), respect 10 sprites/line.

## Input rules
- Read joypad once per frame; act on edges (`pressed = keys & ~prev`) for menus and one-shot actions.
- Never require frame-perfect inputs; buffers and coyote windows are cheap.
- Menus: auto-repeat on held D-pad (DAS 20/6), A confirms, B goes back, Start = confirm on title.
