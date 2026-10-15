"""MADRIGUERA M1 (GDD 10, test plan 11): title, Tilo's movement and walls, corner sliding through a
doorway, the room slide, the sword against a babosa, damage/knockback/invulnerability, death -> FIN ->
continue, the heart pickup; and what the player sees (vram_errors, mockups, the room == the map)."""
from maz_nav import RULES as R, SC_FIN, SC_PLAY, SC_TITLE, enemies, new_game, place, room_errors, settle


def test_title_is_its_mockup_with_proportional_text(gb):
    gb.frames(10)
    assert gb.u8("scene") == SC_TITLE
    assert gb.mockup_errors("title", ignore=["PULSA_START"]) == []
    assert gb.vram_errors("title") == []
    seen = set()
    for _ in range(64):                           # it blinks 30/30 f
        gb.frames(1)
        seen |= {gb.read_text(r) for r in range(14, 18)}
    assert "Pulsa Start" in seen, seen
    gb.screenshot("title")


def test_new_game_starts_in_the_entrance(gb):
    new_game(gb)
    assert (gb.u8("room_c"), gb.u8("room_r")) == (1, 3)
    assert gb.u8("hp") == gb.u8("hp_max") == R["HP_START"]
    assert gb.u8("en_alive") == 2
    assert gb.mockup_errors("play", (0, 0, 20, 2)) == []     # 3 full hearts
    assert room_errors(gb) == []
    assert gb.vram_errors("play") == []
    gb.screenshot("r1")


def test_walk_speed_is_exact_and_walls_stop(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)                 # invincible, frozen enemies: only the walls count
    place(gb, 192, 432)                           # row 27 of R1 is free from col 11 to 18
    gb.hold("right", 32)
    assert gb.u16("lx") == 192 + 32 * R["LINK_SPEED"] // 256          # 1.25 px/f: 40 px in 32 f
    gb.hold("left", 200)
    assert gb.u16("lx") == 11 * 16 - 3                               # feet box x+3 on the wall
    x = gb.u16("lx")
    gb.hold("left", 30)
    assert gb.u16("lx") == x


def test_corner_slide_through_the_door_and_room_slide(gb):
    new_game(gb)
    place(gb, 243, 420, "up")                    # 3 px off the 16 px doorway (cols 232-247)
    lost = 0
    for _ in range(140):
        gb.hold("up", 1)
        lost = max(lost, gb.u16("world_lost"))
        if gb.u8("room_r") == 2:
            break
    assert gb.u8("room_r") == 2, "did not slide into the doorway"
    assert settle(gb)
    assert lost == 0 and gb.u16("world_lost") == 0 and gb.u8("vram_late") == 0
    assert room_errors(gb) == []
    assert gb.vram_errors("play") == []           # also right after the transition
    ly = gb.u16("ly")
    assert 2 * 8 * 16 + 16 <= ly + 12 < 3 * 8 * 16 - 16, ly        # inside R2, not in its doorway
    gb.screenshot("r2")


def test_sword_kills_a_babosa(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 2)                 # frozen enemies
    gb.frames(2)
    i, ex, ey = enemies(gb)[0]
    place(gb, ex * 16 - 18, ey * 16, "right")     # just left of it, facing it
    alive = gb.u8("en_alive")
    gb.tap("a")
    gb.frames(30)
    gb.tap("a")
    gb.frames(10)
    gb.screenshot("sword_kill")
    assert gb.u8("en_alive") == alive - 1


def test_hurt_knockback_and_invulnerability(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 2)
    gb.frames(2)
    i, ex, ey = enemies(gb)[0]
    place(gb, ex * 16 + 8, ey * 16)               # overlapping it from the right
    gb.frames(3)
    assert gb.u8("hp") == R["HP_START"] - 1
    assert gb.u8("inv_t") > 0
    gb.frames(12)
    assert gb.u16("lx") > ex * 16 + 8                # pushed away (right), walls permitting
    place(gb, ex * 16 + 8, ey * 16)
    gb.frames(20)
    assert gb.u8("hp") == R["HP_START"] - 1       # still invulnerable


def test_death_fin_and_continue(gb):
    new_game(gb)
    entry = (gb.u16("lx"), gb.u16("ly"))
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("hp", 1)
    i, ex, ey = enemies(gb)[0]
    place(gb, ex * 16 + 8, ey * 16)
    assert settle(gb, SC_FIN, 300)
    gb.frames(5)
    assert gb.mockup_errors("fin") == []
    assert gb.vram_errors("gameover") == []
    assert gb.read_text(6) == "Has caido."
    gb.screenshot("fin")
    gb.tap("a")                                   # Continuar
    assert settle(gb, SC_PLAY, 300)
    assert gb.u8("hp") == gb.u8("hp_max")
    assert (gb.u16("lx"), gb.u16("ly")) == entry
    assert gb.u16("deaths") == 1
    assert gb.vram_errors("play") == []


def test_heart_pickup_heals(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("hp", 2)
    place(gb, 240, 448)
    gb.write_bytes("pk_x", [(240 - 176 + 16) + 4])   # screen x of Tilo (+4), room col 1 = screen 16
    gb.write_bytes("pk_y", [448 - 368])
    gb.write_u16("pk_t", 200)
    gb.frames(3)
    assert gb.u8("hp") == 2 + R["HEART_HEAL"]


def test_frame_budget_bot_visits_the_three_rooms(gb):
    """A bot that walks the M1 route (R1 -> R2 -> R3 -> back) swinging the sword; it must reach the
    rooms (a stuck bot measures nothing)."""
    new_game(gb)
    gb.write_u8("cheat_flags", 1)                 # invincible: this test measures, it does not fight
    gb.write_u8("max_frame_lines", 0)
    route = [("up", 2), ("left", None)]
    seen = {(1, 3)}
    worst = 0
    for f in range(2400):
        room = (gb.u8("room_c"), gb.u8("room_r"))
        seen.add(room)
        lx, ly = gb.u16("lx"), gb.u16("ly")
        if room == (1, 3):                       # to the top door (cols 232-247)
            d = "left" if lx > 236 else "right" if lx < 236 else "up"
        elif room == (1, 2):                     # round the stumps (cols 14-15, rows 19-20) to the
            d = "left" if lx > 190 and ly > 330 else "up" if ly > 308 else "left"   # left door
        else:
            d = "right" if f % 400 < 200 else "up"
        gb.pyboy.button_press(d)
        if f % 37 == 0:
            gb.pyboy.button_press("a")
        gb.frames(1)
        gb.pyboy.button_release(d)
        gb.pyboy.button_release("a")
        worst = max(worst, gb.u8("max_frame_lines"))
        if gb.u8("scene") != SC_PLAY:
            break
    assert {(1, 3), (1, 2), (0, 2)} <= seen, seen
    assert gb.u8("vram_late") == 0 and gb.u16("world_lost") == 0
    print("worst lines", worst)
    assert worst < 100
