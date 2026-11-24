<!-- Pan Docs: Palettes.md (gbdev/pandocs, CC0) -->
# Palettes

## LCD Monochrome Palettes

Non-Color games have access to one palette for the background (and Window), and two for OBJs.

In CGB Mode the color palettes are taken from [CGB palette memory](<#LCD Color Palettes (CGB only)>)
instead.

### FF47 — BGP (Non-CGB Mode only): BG palette data

This register assigns gray shades to the [color indices](<#Data format>) of the BG and Window tiles.

| Color for... | 7-6 | 5-4 | 3-2 | 1-0 |
|---|---|---|---|---|
| | ID 3 | ID 2 | ID 1 | ID 0 |


Each of the two-bit values map to a color thusly:

Value | Color
------|-------
  0   | White
  1   | Light gray
  2   | Dark gray
  3   | Black

### FF48–FF49 — OBP0, OBP1 (Non-CGB Mode only): OBJ palette 0, 1 data

These registers assigns gray shades to the color indexes of the OBJs that use the corresponding palette.
They work exactly like [`BGP`](<#FF47 — BGP (Non-CGB Mode only): BG palette data>), except that the lower two bits are ignored because color index 0 is transparent for OBJs.

## LCD Color Palettes (CGB only)

The GBC provides 8 palettes for the background (and Window), and 8 for OBJs; they are selected via the [attribute maps](<#BG Map Attributes (CGB Mode only)>) and [OAM attributes](<#Byte 3 — Attributes/Flags>) respectively.

:::tip NOTE

All background colors are initialized as white [by the boot ROM](<#Power-Up Sequence>).

:::

Colors on the Game Boy Color are stored as RGB555, meaning a single color is composed of three 5-bit components, one for each of red, green, and blue.
Each 15-bit color occupies the lower part of a 16-bit word[^bit15]:

<svg viewBox="0 -21 335 101" id="rgb555">
	<defs>
		<style type="text/css"><![CDATA[
			#rgb555 rect {
				fill: none;
				stroke: var(--fg, #000);
			}
			#rgb555 text {
				fill: var(--fg, #000);
				font-size: 7.5px;
				dominant-baseline: middle;
				text-anchor: middle;
			}
			#rgb555 .left  { text-anchor: start; }
			#rgb555 .right { text-anchor: end; }
			#rgb555 .sm { font-size: 7px; }
			#rgb555 path { stroke-width: .5px; }
			#rgb555 polyline, line {
				fill: none;
				stroke: var(--fg, #000);
				stroke-width: .5px;
			}
			#rgb555 .thick { stroke-width: 1px; }
			#rgb555 .dashed {
				stroke-dasharray: 1;
			}
		]]></style>
		<linearGradient id="fg-black" gradientTransform="rotate(90)">
			<stop offset="0%"   stop-color="black"/>
			<stop offset="100%" stop-color="var(--fg)"/>
		</linearGradient>
	</defs>
	<image x="240" y="30" href="imgs/palette_viewer_screenshot.png" width="94" height="45"/>
	<rect x="264" y="-20" width="8" height="8" style="fill:#8439FF"/>
	<polyline points="285,55 276,55 276,-16 270,-16" style="stroke:#8439FF"/>
	<text x="261" y="-16" class="right"><tspan class="sm">8-bit RGB color:</tspan> #8439FF</text>
	<polyline points="259,-12 254,-12 256.5,-12 256.5,-3 211,-3 211,1 208,1 214,1"/>
	<polyline points="251,-12 245,-12 248,-12 248,-6 136,-6 136,1 133,1 139,1"/>
	<polyline points="242,-12 236,-12 239,-12 239,-9 50,-9 50,1 47,1 53,1"/>
	<text x="41"  y="6.5" class="sm">8-bit red: $84 (132)</text>
	<rect x="1"   y="11" width="80" height="10" style="fill:#f005"/><text x="6"   y="17" class="sm">1</text>
	<line x1="11"  y1="11" x2="11"  y2="21" opacity="0.7"/>         <text x="16"  y="17" class="sm">0</text>
	<line x1="21"  y1="11" x2="21"  y2="21" opacity="0.7"/>         <text x="26"  y="17" class="sm">0</text>
	<line x1="31"  y1="11" x2="31"  y2="21" opacity="0.7"/>         <text x="36"  y="17" class="sm">0</text>
	<line x1="41"  y1="11" x2="41"  y2="21" opacity="0.7"/>         <text x="46"  y="17" class="sm">0</text>
	<line x1="51"  y1="11" x2="51"  y2="21" opacity="0.7"/>         <text x="56"  y="17" class="sm">1</text>
	<line x1="61"  y1="11" x2="61"  y2="21" opacity="0.7"/>         <text x="66"  y="17" class="sm">0</text>
	<line x1="71"  y1="11" x2="71"  y2="21" opacity="0.7"/>         <text x="76"  y="17" class="sm">0</text>
	<text x="121" y="6.5" class="sm">8-bit green: $39 (57)</text>
	<rect x="81"  y="11" width="80" height="10" style="fill:#0f04"/><text x="86"  y="17" class="sm">0</text>
	<line x1="91"  y1="11" x2="91"  y2="21" opacity="0.7"/>         <text x="96"  y="17" class="sm">0</text>
	<line x1="101" y1="11" x2="101" y2="21" opacity="0.7"/>         <text x="106" y="17" class="sm">1</text>
	<line x1="111" y1="11" x2="111" y2="21" opacity="0.7"/>         <text x="116" y="17" class="sm">1</text>
	<line x1="121" y1="11" x2="121" y2="21" opacity="0.7"/>         <text x="126" y="17" class="sm">1</text>
	<line x1="131" y1="11" x2="131" y2="21" opacity="0.7"/>         <text x="136" y="17" class="sm">0</text>
	<line x1="141" y1="11" x2="141" y2="21" opacity="0.7"/>         <text x="146" y="17" class="sm">0</text>
	<line x1="151" y1="11" x2="151" y2="21" opacity="0.7"/>         <text x="156" y="17" class="sm">1</text>
	<text x="201" y="6.5" class="sm">8-bit blue: $FF (255)</text>
	<rect x="161" y="11" width="80" height="10" style="fill:#00f5"/><text x="166" y="17" class="sm">1</text>
	<line x1="171" y1="11" x2="171" y2="21" opacity="0.7"/>         <text x="176" y="17" class="sm">1</text>
	<line x1="181" y1="11" x2="181" y2="21" opacity="0.7"/>         <text x="186" y="17" class="sm">1</text>
	<line x1="191" y1="11" x2="191" y2="21" opacity="0.7"/>         <text x="196" y="17" class="sm">1</text>
	<line x1="201" y1="11" x2="201" y2="21" opacity="0.7"/>         <text x="206" y="17" class="sm">1</text>
	<line x1="211" y1="11" x2="211" y2="21" opacity="0.7"/>         <text x="216" y="17" class="sm">1</text>
	<line x1="221" y1="11" x2="221" y2="21" opacity="0.7"/>         <text x="226" y="17" class="sm">1</text>
	<line x1="231" y1="11" x2="231" y2="21" opacity="0.7"/>         <text x="236" y="17" class="sm">1</text>
	<path d="M81,31  c0,15 9,15    9,30    h50 c0,-15 -9,-15   -9,-30   Z" fill="var(--bg)" stroke="var(--fg)"/>
	<path d="M81,31  c0,15 9,15    9,30    h50 c0,-15 -9,-15   -9,-30   Z" fill="#0f04" stroke="#0f04"/>
	<rect x="81"  y="21" width="50" height="10"/>
	<text x="106" y="26.5">5-bit green: 7</text>
	<path d="M161,31 c0,15 -121,15 -121,30 h50 c0,-15 121,-15  121,-30  Z" fill="var(--bg)" stroke="var(--fg)"/>
	<path d="M161,31 c0,15 -121,15 -121,30 h50 c0,-15 121,-15  121,-30  Z" fill="#00f5" stroke="#00f5"/>
	<rect x="161" y="21" width="50" height="10"/>
	<text x="186" y="26.5">5-bit blue: 31</text>
	<path d="M1,31   c0,15 139,15  139,30  h50 c0,-15 -139,-15 -139,-30 Z" fill="var(--bg)" stroke="var(--fg)"/>
	<path d="M1,31   c0,15 139,15  139,30  h50 c0,-15 -139,-15 -139,-30 Z" fill="#f005" stroke="#f005"/>
	<rect x="1"   y="21" width="50" height="10"/>
	<text x="26"  y="26.5">5-bit red: 16</text>
	<rect x="40"  y="61" width="50" height="10" style="stroke:none;fill:#00f5"/>
	<rect x="90"  y="61" width="50" height="10" style="stroke:none;fill:#0f04"/>
	<rect x="140" y="61" width="50" height="10" style="stroke:none;fill:#f005"/>
	<rect x="30"   y="61" width="80" height="10"/><line x1="30" y1="71" x2="40" y2="61"/>
	<line x1="40"  y1="61" x2="40"  y2="71"/>     <text x="45"  y="67">1</text>
	<line x1="50"  y1="61" x2="50"  y2="71"/>     <text x="55"  y="67">1</text>
	<line x1="60"  y1="61" x2="60"  y2="71"/>     <text x="65"  y="67">1</text>
	<line x1="70"  y1="61" x2="70"  y2="71"/>     <text x="75"  y="67">1</text>
	<line x1="80"  y1="61" x2="80"  y2="71"/>     <text x="85"  y="67">1</text>
	<line x1="90"  y1="61" x2="90"  y2="71"/>     <text x="95"  y="67">0</text>
	<line x1="100" y1="61" x2="100" y2="71"/>     <text x="105" y="67">0</text>
	<polyline points="31,72 31,76 53,76"/><polyline points="87,76 109,76 109,72"/>
	<text x="70"  y="76" class="sm">High byte</text>
	<rect x="110"  y="61" width="80" height="10"/><text x="115" y="67">1</text>
	<line x1="120" y1="61" x2="120" y2="71"/>     <text x="125" y="67">1</text>
	<line x1="130" y1="61" x2="130" y2="71"/>     <text x="135" y="67">1</text>
	<line x1="140" y1="61" x2="140" y2="71"/>     <text x="145" y="67">1</text>
	<line x1="150" y1="61" x2="150" y2="71"/>     <text x="155" y="67">0</text>
	<line x1="160" y1="61" x2="160" y2="71"/>     <text x="165" y="67">0</text>
	<line x1="170" y1="61" x2="170" y2="71"/>     <text x="175" y="67">0</text>
	<line x1="180" y1="61" x2="180" y2="71"/>     <text x="185" y="67">0</text>
	<polyline points="111,72 111,76 134,76"/><polyline points="166,76 189,76 189,72"/>
	<text x="150" y="76" class="sm">Low byte</text>
	<text x="193" y="67" class="left">= $7CF0</text>
	<text x="212" y="49" class="sm">5-bit RGB</text>
	<text x="212" y="57" class="sm">color:</text>
	<polyline points="290,68 280,68 285,68 285,75" style="stroke:url('#fg-black')"/>
	<polyline points="285,75 285,78 214,78 214,71 223,71 205,71"/>
</svg>


The color palettes are stored in two dedicated banks of palette RAM (or <abbr title="Color RAM">CRAM</abbr> for *color RAM*), 64 bytes each[^cram_size]: one for background/window palettes and the other for OBJ palettes.

The two bytes of each color are stored in **little-endian** byte order, meaning that the low byte comes first.
For example, the two palettes shown in the previous diagram would be stored like this:

<svg viewBox="-15 0 365 32" id="cram">
	<defs>
		<style type="text/css"><![CDATA[
			#cram rect {
				stroke: var(--fg, #000);
			}
			#cram text {
				fill: var(--fg, #000);
				font-size: 7px;
				dominant-baseline: middle;
				text-anchor: middle;
			}
			#cram .left  { text-anchor: start; }
			#cram .right { text-anchor: end; }
			#cram .byte { font-size: 7.5px; }
			#cram polyline, line {
				fill: none;
				stroke: var(--fg, #000);
				stroke-width: .5px;
			}
			#cram .thick { stroke-width: 1px; }
			#cram .dashed { stroke-dasharray: 1; }
		]]></style>
	</defs>
	<text x="2" y="4.5" class="right" style="font-size:6px">Addr:</text>
	<polygon points="341,8 341,18 321,18 321,8" fill="#ffffff"/>
	<rect x="281" y="8" width="40" height="10" fill="#FF8484"/><line x1="301" y1="8"  x2="301" y2="18"/>
	<rect x="241" y="8" width="40" height="10" fill="#FF0000"/><line x1="261" y1="8"  x2="261" y2="18"/>
	<rect x="201" y="8" width="40" height="10" fill="#8439FF"/><line x1="221" y1="8"  x2="221" y2="18"/>
	<rect x="161" y="8" width="40" height="10" fill="#FFFFFF"/><line x1="181" y1="8"  x2="181" y2="18"/>
	<rect x="121" y="8" width="40" height="10" fill="#FFA594"/><line x1="141" y1="8"  x2="141" y2="18"/>
	<rect x="81"  y="8" width="40" height="10" fill="#8439FF"/><line x1="101" y1="8"  x2="101" y2="18"/>
	<rect x="41"  y="8" width="40" height="10" fill="#420031"/><line x1="61"  y1="8"  x2="61"  y2="18"/>
	<rect x="1"   y="8" width="40" height="10" fill="#FFFFFF"/><line x1="21"  y1="8"  x2="21"  y2="18"/>
	<text x="11"  y="5">00</text><text x="11"  y="14" class="byte" style="fill:#000">$FF</text>
	<text x="31"  y="5">01</text><text x="31"  y="14" class="byte" style="fill:#000">$7F</text>
	<text x="51"  y="5">02</text><text x="51"  y="14" class="byte" style="fill:#fff">$08</text>
	<text x="71"  y="5">03</text><text x="71"  y="14" class="byte" style="fill:#fff">$18</text>
	<text x="91"  y="5">04</text><text x="91"  y="14" class="byte" style="fill:#fff">$F0</text>
	<text x="111" y="5">05</text><text x="111" y="14" class="byte" style="fill:#fff">$7C</text>
	<text x="131" y="5">06</text><text x="131" y="14" class="byte" style="fill:#000">$9F</text>
	<text x="151" y="5">07</text><text x="151" y="14" class="byte" style="fill:#000">$4A</text>
	<polyline points="2,19 2,23 73,23"/><polyline points="89,23 160,23 160,19"/><text x="81" y="24">BG0</text>
	<text x="171" y="5">08</text><text x="171" y="14" class="byte" style="fill:#000">$FF</text>
	<text x="191" y="5">09</text><text x="191" y="14" class="byte" style="fill:#000">$7F</text>
	<text x="211" y="5">0A</text><text x="211" y="14" class="byte" style="fill:#fff">$F0</text>
	<text x="231" y="5">0B</text><text x="231" y="14" class="byte" style="fill:#fff">$7C</text>
	<text x="251" y="5">0C</text><text x="251" y="14" class="byte" style="fill:#fff">$1F</text>
	<text x="271" y="5">0D</text><text x="271" y="14" class="byte" style="fill:#fff">$00</text>
	<text x="291" y="5">0E</text><text x="291" y="14" class="byte" style="fill:#000">$1F</text>
	<text x="311" y="5">0F</text><text x="311" y="14" class="byte" style="fill:#000">$42</text>
	<polyline points="162,19 162,23 233,23"/><polyline points="249,23 320,23 320,19"/><text x="241" y="24">BG1</text>
	<text x="331" y="5">10</text><text x="331" y="14" class="byte" style="fill:#000">$FF</text>
	<line x1="321" y1="8"  x2="342" y2="8"  class="thick"/><line x1="342" y1="8"  x2="350" y2="8"  class="thick dashed"/>
	<line x1="321" y1="18" x2="342" y2="18" class="thick"/><line x1="342" y1="18" x2="350" y2="18" class="thick dashed"/>
	<polyline points="322,19 322,23 326,23"/><line x1="342" y1="23" x2="350" y2="23" class="dashed"/><text x="334" y="24">BG2</text>
</svg>


Unlike VRAM, OAM, or wave RAM, CRAM is not exposed in the memory map and cannot be accessed directly.
Instead, each bank of CRAM is accessed through a pair of registers: one register is used to select a CRAM address, and the other provides read/write access to the byte at that address.
Much like VRAM, the CRAM data registers are inaccessible when the PPU is reading from CRAM, that is, during [Mode 3](<#PPU modes>): writes are ignored, and reads return $FF.

[^bit15]:
The 16th bit, bit 15, is **ignored** by the rendering process.
Conventionally, that bit is generally clear (for example, the canonical pure white is `$7FFF` and not `$FFFF`), but the hardware treats both identically: it's fine to fill color RAM with $FF bytes to set it to all-white.

[^cram_size]:
2 bytes/color × 4 colors/palette × 8 palettes = 64 bytes.

### FF68 — BGPI (CGB Mode only): Background palette index

| BGPI | 7 | 5-0 |
|---|---|---|
| | Auto-increment | Address |


- **Auto-increment**: `0` = Disabled; `1` = Enabled
- **Address**: Specifies which byte of BG Palette Memory can be accessed through
  [`BGPD`](<#FF69 — BGPD (CGB Mode only): Background palette data>)

Unlike `BGPD`, this register can be freely accessed outside VBlank and HBlank.

### FF69 — BGPD (CGB Mode only): Background palette data

As each color is two bytes in size, you must read/write this register *twice* to access a whole color.

This is made much easier through the use of the address auto-increment: `BGPI`'s "address" field is automatically incremented (wrapping around from 63 back to 0) after each write to this register, even if the write fails due to CRAM being inaccessible.
Reads, however, never trigger auto-increment.

### FF6A–FF6B — OBPI, OBPD (CGB Mode only): OBJ palette index, OBJ palette data

These registers function exactly like BGPI and BGPD respectively; the 64 bytes of OBJ palette memory are entirely separate from Background palette memory, but function the same.

Note that while 4 colors are stored per OBJ palette, color #0 is never used, as it's always transparent. It's thus fine to write garbage values, or even leave it uninitialized.

:::tip NOTE

In CGB mode, the boot ROM leaves all object colors uninitialized (and thus somewhat random/unreliable), aside from setting the first byte of OBJ0 color #0 to $00, which is unused.

In DMG compatibility mode, the boot ROM sets the first 2 object palettes which are used by OBP0/OBP1, [as explained here](<#Compatibility palettes>).

:::

### RGB Translation by CGBs

(image: sRGB versus CGB color mixing)

When developing graphics on PCs, note that the RGB values will have
different appearance on CGB displays as on VGA/HDMI monitors calibrated
to sRGB color. Because the GBC is not lit, the highest intensity will
produce light gray rather than white. The intensities are not
linear; the values $10-$1F will all appear very bright, while medium and
darker colors are ranged at $00-0F.

The CGB display's pigments aren't perfectly saturated. This means the
colors mix quite oddly: increasing the intensity of only one R/G/B color
will also influence the other two R/G/B colors. For example, a color
setting of $03EF (Blue=$00, Green=$1F, Red=$0F) will appear as Neon Green
on VGA displays, but on the CGB it'll produce a decently washed out
Yellow. See the image above.

### RGB Translation by GBAs

Even though GBA is described to be compatible to CGB games, most CGB
games are completely unplayable on older GBAs because most colors are
invisible (black). Of course, colors such like Black and White will
appear the same on both CGB and GBA, but medium intensities are arranged
completely different. Intensities in range $00–07 are invisible/black
(unless eventually under best sunlight circumstances, and when gazing at
the screen under obscure viewing angles), unfortunately, these
intensities are regularly used by most existing CGB games for medium and
darker colors.

:::tip WORKAROUND

Newer CGB games may avoid this effect by changing palette data when
detecting GBA hardware ([see how](<#Detecting CGB (and GBA) functions>)).
Based on measurements of GBC and GBA palettes using the
[144p Test Suite](https://github.com/pinobatch/240p-test-mini/tree/master/gameboy),
a fairly close approximation is `GBA = GBC × 3/4 + $08` for each R/G/B
component. The result isn't quite perfect, and it may turn
out that the color mixing is different also; anyways, it'd be still
ways better than no conversion.

:::

This problem with low brightness levels does not affect later GBA SP
units and Game Boy Player. Thus ideally, the player should have control
of this brightness correction.
