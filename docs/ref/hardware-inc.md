# hardware.inc names (with GBDK equivalents)

From the gbdev `hardware.inc` bundled with hUGEDriver (`reference/hugedriver_dl/hUGEDriver/include/hardware.inc`,
public domain) and GBDK's `gb/hardware.h` (gb target). `rXXX` names exist in both; GBDK C code usually
writes `XXX_REG` (column GBDK). Bit names (`LCDCF_*`, `STATF_*`...) are the hardware.inc ones; GBDK
defines the same `LCDCF_*`/`STATF_*` macros for the gb target. `%` = binary, `$` = hex.

| Name | Value | GBDK | Comment |
|---|---|---|---|
| `HARDWARE_INC` | `1` |  | Usage: rev_Check_hardware_inc <min_ver> |
| `_VRAM` | `$8000` |  | $8000->$9FFF |
| `_SCRN0` | `$9800` |  | $9800->$9BFF |
| `_SCRN1` | `$9C00` |  | $9C00->$9FFF |
| `_SRAM` | `$A000` |  | $A000->$BFFF |
| `_RAM` | `$C000` |  | $C000->$CFFF / $C000->$DFFF |
| `_RAMBANK` | `$D000` |  | $D000->$DFFF |
| `_OAMRAM` | `$FE00` |  | $FE00->$FE9F |
| `_IO` | `$FF00` |  | $FF00->$FF7F,$FFFF |
| `_AUD3WAVERAM` | `$FF30` |  | $FF30->$FF3F |
| `_HRAM` | `$FF80` |  | $FF80->$FFFE |
| `rRAMG` | `$0000` |  |  |
| `CART_SRAM_ENABLE` | `$0A` |  |  |
| `CART_SRAM_DISABLE` | `$00` |  | -- |
| `rROMB0` | `$2000` |  | -- |
| `rRAMB` | `$4000` |  | *** MBC3-specific registers *** |
| `RTC_S` | `$08` |  | Seconds  (0-59) |
| `RTC_M` | `$09` |  | Minutes  (0-59) |
| `RTC_H` | `$0A` |  | Hours    (0-23) |
| `RTC_DL` | `$0B` |  | Lower 8 bits of Day Counter ($00-$FF) |
| `RTC_DH` | `$0C` |  | Bit 7 - Day Counter Carry Bit (1=Counter Overflow) |
| `rRTCLATCH` | `$6000` |  | *** MBC5-specific register *** |
| `rROMB1` | `$3000` |  | Bit 3 of RAMB enables the rumble motor (if any) |
| `CART_RUMBLE_ON` | `1 << 3` |  | *************************************************************************** |
| `rP1` | `$FF00` | `P1_REG` | Joystick register @see joypad(), add_JOY(), IEF_HILO, P1F_5, P1F_4, P1F_3, P1F_2, P1F_1, P1F_0, P1F_GET_DPAD, P1F_GET_BTN, P1F_GET_NONE |
| `P1F_5` | `%00100000` |  | P15 out port, set to 0 to get buttons |
| `P1F_4` | `%00010000` |  | P14 out port, set to 0 to get dpad |
| `P1F_3` | `%00001000` |  | P13 in port |
| `P1F_2` | `%00000100` |  | P12 in port |
| `P1F_1` | `%00000010` |  | P11 in port |
| `P1F_0` | `%00000001` |  | P10 in port |
| `P1F_GET_DPAD` | `P1F_5` |  |  |
| `P1F_GET_BTN` | `P1F_4` |  |  |
| `P1F_GET_NONE` | `P1F_4 | P1F_5` |  | -- |
| `rSB` | `$FF01` | `SB_REG` | -- |
| `rSC` | `$FF02` | `SC_REG` | Serial IO control register |
| `SCF_START` | `%10000000` |  | Transfer Start Flag (1=Transfer in progress, or requested) |
| `SCF_SPEED` | `%00000010` |  | Clock Speed (0=Normal, 1=Fast) ** CGB Mode Only ** |
| `SCF_SOURCE` | `%00000001` |  | Shift Clock (0=External Clock, 1=Internal Clock) |
| `SCB_START` | `7` |  |  |
| `SCB_SPEED` | `1` |  |  |
| `SCB_SOURCE` | `0` |  | -- |
| `rDIV` | `$FF04` | `DIV_REG` | -- |
| `rTIMA` | `$FF05` | `TIMA_REG` | -- |
| `rTMA` | `$FF06` | `TMA_REG` | -- |
| `rTAC` | `$FF07` | `TAC_REG` | Timer control |
| `TACF_START` | `%00000100` |  |  |
| `TACF_STOP` | `%00000000` |  |  |
| `TACF_4KHZ` | `%00000000` |  |  |
| `TACF_16KHZ` | `%00000011` |  |  |
| `TACF_65KHZ` | `%00000010` |  |  |
| `TACF_262KHZ` | `%00000001` |  |  |
| `TACB_START` | `2` |  | -- |
| `rIF` | `$FF0F` | `IF_REG` | -- |
| `rNR10` | `$FF10` |  |  |
| `rAUD1SWEEP` | `rNR10` | `NR10_REG` | Sound Channel 1, NR10: Sweep |
| `AUD1SWEEP_UP` | `%00000000` |  |  |
| `AUD1SWEEP_DOWN` | `%00001000` |  | -- |
| `rNR11` | `$FF11` |  |  |
| `rAUD1LEN` | `rNR11` | `NR11_REG` | -- |
| `rNR12` | `$FF12` |  |  |
| `rAUD1ENV` | `rNR12` | `NR12_REG` | -- |
| `rNR13` | `$FF13` |  |  |
| `rAUD1LOW` | `rNR13` | `NR13_REG` | -- |
| `rNR14` | `$FF14` |  |  |
| `rAUD1HIGH` | `rNR14` | `NR14_REG` | -- |
| `rNR21` | `$FF16` |  |  |
| `rAUD2LEN` | `rNR21` | `NR21_REG` | -- |
| `rNR22` | `$FF17` |  |  |
| `rAUD2ENV` | `rNR22` | `NR22_REG` | -- |
| `rNR23` | `$FF18` |  |  |
| `rAUD2LOW` | `rNR23` | `NR23_REG` | -- |
| `rNR24` | `$FF19` |  |  |
| `rAUD2HIGH` | `rNR24` | `NR24_REG` | -- |
| `rNR30` | `$FF1A` |  |  |
| `rAUD3ENA` | `rNR30` | `NR30_REG` | Sound Channel 3, NR30_REG: Sound on/off |
| `AUD3ENA_OFF` | `%00000000` |  |  |
| `AUD3ENA_ON` | `%10000000` |  | -- |
| `rNR31` | `$FF1B` |  |  |
| `rAUD3LEN` | `rNR31` | `NR31_REG` | -- |
| `rNR32` | `$FF1C` |  |  |
| `rAUD3LEVEL` | `rNR32` | `NR32_REG` | Sound Channel 3, NR32_REG: Select output level |
| `AUD3LEVEL_MUTE` | `%00000000` |  |  |
| `AUD3LEVEL_100` | `%00100000` |  |  |
| `AUD3LEVEL_50` | `%01000000` |  |  |
| `AUD3LEVEL_25` | `%01100000` |  | -- |
| `rNR33` | `$FF1D` |  |  |
| `rAUD3LOW` | `rNR33` | `NR33_REG` | -- |
| `rNR34` | `$FF1E` |  |  |
| `rAUD3HIGH` | `rNR34` | `NR34_REG` | -- |
| `rNR41` | `$FF20` |  |  |
| `rAUD4LEN` | `rNR41` | `NR41_REG` | -- |
| `rNR42` | `$FF21` |  |  |
| `rAUD4ENV` | `rNR42` | `NR42_REG` | -- |
| `rNR43` | `$FF22` |  |  |
| `rAUD4POLY` | `rNR43` | `NR43_REG` | Sound Channel 4, NR43_REG: Polynomial Counter |
| `AUD4POLY_15STEP` | `%00000000` |  |  |
| `AUD4POLY_7STEP` | `%00001000` |  | -- |
| `rNR44` | `$FF23` |  |  |
| `rAUD4GO` | `rNR44` | `NR44_REG` | -- |
| `rNR50` | `$FF24` |  |  |
| `rAUDVOL` | `rNR50` | `NR50_REG` | Sound Master Volume, NR50: Volume and Cart external sound input (VIN) |
| `AUDVOL_VIN_LEFT` | `%10000000` |  | SO2 |
| `AUDVOL_VIN_RIGHT` | `%00001000` |  | SO1 |
| `rNR51` | `$FF25` |  |  |
| `rAUDTERM` | `rNR51` | `NR51_REG` | SO2 |
| `AUDTERM_4_LEFT` | `%10000000` |  |  |
| `AUDTERM_3_LEFT` | `%01000000` |  |  |
| `AUDTERM_2_LEFT` | `%00100000` |  |  |
| `AUDTERM_1_LEFT` | `%00010000` |  | SO1 |
| `AUDTERM_4_RIGHT` | `%00001000` |  |  |
| `AUDTERM_3_RIGHT` | `%00000100` |  |  |
| `AUDTERM_2_RIGHT` | `%00000010` |  |  |
| `AUDTERM_1_RIGHT` | `%00000001` |  | -- |
| `rNR52` | `$FF26` |  |  |
| `rAUDENA` | `rNR52` | `NR52_REG` | Sound Master Control, NR52: ON / OFF |
| `AUDENA_ON` | `%10000000` |  |  |
| `AUDENA_OFF` | `%00000000` |  | sets all audio regs to 0! |
| `rLCDC` | `$FF40` | `LCDC_REG` | LCD control |
| `LCDCF_OFF` | `%00000000` |  | LCD Control Operation |
| `LCDCF_ON` | `%10000000` |  | LCD Control Operation |
| `LCDCF_WIN9800` | `%00000000` |  | Window Tile Map Display Select |
| `LCDCF_WIN9C00` | `%01000000` |  | Window Tile Map Display Select |
| `LCDCF_WINOFF` | `%00000000` |  | Window Display |
| `LCDCF_WINON` | `%00100000` |  | Window Display |
| `LCDCF_BG8800` | `%00000000` |  | BG & Window Tile Data Select |
| `LCDCF_BG8000` | `%00010000` |  | BG & Window Tile Data Select |
| `LCDCF_BG9800` | `%00000000` |  | BG Tile Map Display Select |
| `LCDCF_BG9C00` | `%00001000` |  | BG Tile Map Display Select |
| `LCDCF_OBJ8` | `%00000000` |  | OBJ Construction |
| `LCDCF_OBJ16` | `%00000100` |  | OBJ Construction |
| `LCDCF_OBJOFF` | `%00000000` |  | OBJ Display |
| `LCDCF_OBJON` | `%00000010` |  | OBJ Display |
| `LCDCF_BGOFF` | `%00000000` |  | BG Display |
| `LCDCF_BGON` | `%00000001` |  | BG Display |
| `LCDCB_ON` | `7` |  | LCD Control Operation |
| `LCDCB_WIN9C00` | `6` |  | Window Tile Map Display Select |
| `LCDCB_WINON` | `5` |  | Window Display |
| `LCDCB_BG8000` | `4` |  | BG & Window Tile Data Select |
| `LCDCB_BG9C00` | `3` |  | BG Tile Map Display Select |
| `LCDCB_OBJ16` | `2` |  | OBJ Construction |
| `LCDCB_OBJON` | `1` |  | OBJ Display |
| `LCDCB_BGON` | `0` |  | BG Display |
| `rSTAT` | `$FF41` | `STAT_REG` | LCD status |
| `STATF_LYC` | `%01000000` |  | LYC=LY Coincidence (Selectable) |
| `STATF_MODE10` | `%00100000` |  | Mode 10 |
| `STATF_MODE01` | `%00010000` |  | Mode 01 (V-Blank) |
| `STATF_MODE00` | `%00001000` |  | Mode 00 (H-Blank) |
| `STATF_LYCF` | `%00000100` |  | Coincidence Flag |
| `STATF_HBL` | `%00000000` |  | H-Blank |
| `STATF_VBL` | `%00000001` |  | V-Blank |
| `STATF_OAM` | `%00000010` |  | OAM-RAM is used by system |
| `STATF_LCD` | `%00000011` |  | Both OAM and VRAM used by system |
| `STATF_BUSY` | `%00000010` |  | When set, VRAM access is unsafe |
| `STATB_LYC` | `6` |  |  |
| `STATB_MODE10` | `5` |  |  |
| `STATB_MODE01` | `4` |  |  |
| `STATB_MODE00` | `3` |  |  |
| `STATB_LYCF` | `2` |  |  |
| `STATB_BUSY` | `1` |  | -- |
| `rSCY` | `$FF42` | `__REG` | -- |
| `rSCX` | `$FF43` | `SCX_REG` | -- |
| `rLY` | `$FF44` | `LY_REG` | -- |
| `rLYC` | `$FF45` | `LYC_REG` | -- |
| `rDMA` | `$FF46` | `DMA_REG` | -- |
| `rBGP` | `$FF47` | `BGP_REG` | -- |
| `rOBP0` | `$FF48` | `OBP0_REG` | -- |
| `rOBP1` | `$FF49` | `OBP1_REG` | -- |
| `rWY` | `$FF4A` | `WY_REG` | -- |
| `rWX` | `$FF4B` | `WX_REG` | Window X coordinate |
| `WX_OFS` | `7` |  | add this to a screen position to get a WX position |
| `rKEY1` | `$FF4D` | `KEY1_REG` | CPU speed |
| `rSPD` | `rKEY1` | `KEY1_REG` | CPU speed |
| `KEY1F_DBLSPEED` | `%10000000` |  | 0=Normal Speed, 1=Double Speed (R) |
| `KEY1F_PREPARE` | `%00000001` |  | 0=No, 1=Prepare (R/W) |
| `rVBK` | `$FF4F` | `VBK_REG` | -- |
| `rHDMA1` | `$FF51` | `HDMA1_REG` | -- |
| `rHDMA2` | `$FF52` | `HDMA2_REG` | -- |
| `rHDMA3` | `$FF53` | `HDMA3_REG` | -- |
| `rHDMA4` | `$FF54` | `HDMA4_REG` | -- |
| `rHDMA5` | `$FF55` | `HDMA5_REG` | DMA control 5 |
| `HDMA5F_MODE_GP` | `%00000000` |  | General Purpose DMA (W) |
| `HDMA5F_MODE_HBL` | `%10000000` |  | HBlank DMA (W) |
| `HDMA5B_MODE` | `7` |  | DMA mode select (W) |
| `HDMA5F_BUSY` | `%10000000` |  | 0=Busy (DMA still in progress), 1=Transfer complete (R) |
| `rRP` | `$FF56` | `RP_REG` | IR port |
| `RPF_ENREAD` | `%11000000` |  |  |
| `RPF_DATAIN` | `%00000010` |  | 0=Receiving IR Signal, 1=Normal |
| `RPF_WRITE_HI` | `%00000001` |  |  |
| `RPF_WRITE_LO` | `%00000000` |  |  |
| `RPB_LED_ON` | `0` |  |  |
| `RPB_DATAIN` | `1` |  | -- |
| `rBCPS` | `$FF68` | `BCPS_REG` | BG color palette specification |
| `rBGPI` | `rBCPS` |  |  |
| `BCPSF_AUTOINC` | `%10000000` |  | Auto Increment (0=Disabled, 1=Increment after Writing) |
| `BCPSB_AUTOINC` | `7` |  |  |
| `BGPIF_AUTOINC` | `BCPSF_AUTOINC` |  |  |
| `BGPIB_AUTOINC` | `BCPSB_AUTOINC` |  | -- |
| `rBCPD` | `$FF69` | `BCPD_REG` | BG color palette data |
| `rBGPD` | `rBCPD` |  | -- |
| `rOCPS` | `$FF6A` | `OCPS_REG` | OBJ color palette specification |
| `rOBPI` | `rOCPS` |  |  |
| `OCPSF_AUTOINC` | `%10000000` |  | Auto Increment (0=Disabled, 1=Increment after Writing) |
| `OCPSB_AUTOINC` | `7` |  |  |
| `OBPIF_AUTOINC` | `OCPSF_AUTOINC` |  |  |
| `OBPIB_AUTOINC` | `OCPSB_AUTOINC` |  | -- |
| `rOCPD` | `$FF6B` | `OCPD_REG` | OBJ color palette data |
| `rOBPD` | `rOCPD` |  | -- |
| `rSVBK` | `$FF70` | `SVBK_REG` | Selects the WRAM upper region bank (CGB Only). WRAM Banking is NOT officially supported in GBDK and SDCC. The stack must be moved and other special care taken. |
| `rSMBK` | `rSVBK` | `SVBK_REG` | -- |
| `rPCM12` | `$FF76` | `PCM12_REG` | -- |
| `rPCM34` | `$FF77` | `PCM34_REG` | -- |
| `rIE` | `$FFFF` | `IE_REG` | Interrupt enable |
| `IEF_HILO` | `%00010000` |  | Transition from High to Low of Pin number P10-P13 |
| `IEF_SERIAL` | `%00001000` |  | Serial I/O transfer end |
| `IEF_TIMER` | `%00000100` |  | Timer Overflow |
| `IEF_STAT` | `%00000010` |  | STAT |
| `IEF_VBLANK` | `%00000001` |  | V-Blank |
| `IEB_HILO` | `4` |  |  |
| `IEB_SERIAL` | `3` |  |  |
| `IEB_TIMER` | `2` |  |  |
| `IEB_STAT` | `1` |  |  |
| `IEB_VBLANK` | `0` |  | *************************************************************************** |
| `AUDLEN_DUTY_12_5` | `%00000000` |  | 12.5% |
| `AUDLEN_DUTY_25` | `%01000000` |  | 25% |
| `AUDLEN_DUTY_50` | `%10000000` |  | 50% |
| `AUDLEN_DUTY_75` | `%11000000` |  | 75% |
| `AUDENV_UP` | `%00001000` |  |  |
| `AUDENV_DOWN` | `%00000000` |  | -- |
| `AUDHIGH_RESTART` | `%10000000` |  |  |
| `AUDHIGH_LENGTH_ON` | `%01000000` |  |  |
| `AUDHIGH_LENGTH_OFF` | `%00000000` |  | *************************************************************************** |
| `BOOTUP_A_DMG` | `$01` |  | Dot Matrix Game |
| `BOOTUP_A_CGB` | `$11` |  | Color GameBoy |
| `BOOTUP_A_MGB` | `$FF` |  | Mini GameBoy (Pocket GameBoy) |
| `BOOTUP_B_CGB` | `%00000000` |  |  |
| `BOOTUP_B_AGB` | `%00000001` |  | GBA, GBA SP, Game Boy Player, or New GBA SP |
| `CART_COMPATIBLE_DMG` | `$00` |  |  |
| `CART_COMPATIBLE_DMG_GBC` | `$80` |  |  |
| `CART_COMPATIBLE_GBC` | `$C0` |  | $0146 GameBoy/Super GameBoy indicator |
| `CART_INDICATOR_GB` | `$00` |  |  |
| `CART_INDICATOR_SGB` | `$03` |  | $0147 Cartridge type |
| `CART_ROM` | `$00` |  |  |
| `CART_ROM_MBC1` | `$01` |  |  |
| `CART_ROM_MBC1_RAM` | `$02` |  |  |
| `CART_ROM_MBC1_RAM_BAT` | `$03` |  |  |
| `CART_ROM_MBC2` | `$05` |  |  |
| `CART_ROM_MBC2_BAT` | `$06` |  |  |
| `CART_ROM_RAM` | `$08` |  |  |
| `CART_ROM_RAM_BAT` | `$09` |  |  |
| `CART_ROM_MMM01` | `$0B` |  |  |
| `CART_ROM_MMM01_RAM` | `$0C` |  |  |
| `CART_ROM_MMM01_RAM_BAT` | `$0D` |  |  |
| `CART_ROM_MBC3_BAT_RTC` | `$0F` |  |  |
| `CART_ROM_MBC3_RAM_BAT_RTC` | `$10` |  |  |
| `CART_ROM_MBC3` | `$11` |  |  |
| `CART_ROM_MBC3_RAM` | `$12` |  |  |
| `CART_ROM_MBC3_RAM_BAT` | `$13` |  |  |
| `CART_ROM_MBC5` | `$19` |  |  |
| `CART_ROM_MBC5_BAT` | `$1A` |  |  |
| `CART_ROM_MBC5_RAM_BAT` | `$1B` |  |  |
| `CART_ROM_MBC5_RUMBLE` | `$1C` |  |  |
| `CART_ROM_MBC5_RAM_RUMBLE` | `$1D` |  |  |
| `CART_ROM_MBC5_RAM_BAT_RUMBLE` | `$1E` |  |  |
| `CART_ROM_MBC7_RAM_BAT_GYRO` | `$22` |  |  |
| `CART_ROM_POCKET_CAMERA` | `$FC` |  |  |
| `CART_ROM_BANDAI_TAMA5` | `$FD` |  |  |
| `CART_ROM_HUDSON_HUC3` | `$FE` |  |  |
| `CART_ROM_HUDSON_HUC1` | `$FF` |  | $0148 ROM size |
| `CART_ROM_32KB` | `$00` |  | 2 banks |
| `CART_ROM_64KB` | `$01` |  | 4 banks |
| `CART_ROM_128KB` | `$02` |  | 8 banks |
| `CART_ROM_256KB` | `$03` |  | 16 banks |
| `CART_ROM_512KB` | `$04` |  | 32 banks |
| `CART_ROM_1024KB` | `$05` |  | 64 banks |
| `CART_ROM_2048KB` | `$06` |  | 128 banks |
| `CART_ROM_4096KB` | `$07` |  | 256 banks |
| `CART_ROM_8192KB` | `$08` |  | 512 banks |
| `CART_ROM_1152KB` | `$52` |  | 72 banks |
| `CART_ROM_1280KB` | `$53` |  | 80 banks |
| `CART_ROM_1536KB` | `$54` |  | 96 banks |
| `CART_SRAM_NONE` | `0` |  |  |
| `CART_SRAM_8KB` | `2` |  | 1 bank |
| `CART_SRAM_32KB` | `3` |  | 4 banks |
| `CART_SRAM_128KB` | `4` |  | 16 banks |
| `CART_DEST_JAPANESE` | `$00` |  |  |
| `CART_DEST_NON_JAPANESE` | `$01` |  | *************************************************************************** |
| `PADF_DOWN` | `$80` |  |  |
| `PADF_UP` | `$40` |  |  |
| `PADF_LEFT` | `$20` |  |  |
| `PADF_RIGHT` | `$10` |  |  |
| `PADF_START` | `$08` |  |  |
| `PADF_SELECT` | `$04` |  |  |
| `PADF_B` | `$02` |  |  |
| `PADF_A` | `$01` |  |  |
| `PADB_DOWN` | `$7` |  |  |
| `PADB_UP` | `$6` |  |  |
| `PADB_LEFT` | `$5` |  |  |
| `PADB_RIGHT` | `$4` |  |  |
| `PADB_START` | `$3` |  |  |
| `PADB_SELECT` | `$2` |  |  |
| `PADB_B` | `$1` |  |  |
| `PADB_A` | `$0` |  | *************************************************************************** |
| `SCRN_X` | `160` |  | Width of screen in pixels |
| `SCRN_Y` | `144` |  | Height of screen in pixels. Also corresponds to the value in LY at the beginning of VBlank. |
| `SCRN_X_B` | `20` |  | Width of screen in bytes |
| `SCRN_Y_B` | `18` |  | Height of screen in bytes |
| `SCRN_VX` | `256` |  | Virtual width of screen in pixels |
| `SCRN_VY` | `256` |  | Virtual height of screen in pixels |
| `SCRN_VX_B` | `32` |  | Virtual width of screen in bytes |
| `SCRN_VY_B` | `32` |  | Virtual height of screen in bytes |
| `OAM_Y_OFS` | `16` |  | add this to a screen-relative Y position to get an OAM Y position |
| `OAM_X_OFS` | `8` |  | add this to a screen-relative X position to get an OAM X position |
| `OAM_COUNT` | `40` |  | number of OAM entries in OAM RAM |
| `OAMF_PRI` | `%10000000` |  | Priority |
| `OAMF_YFLIP` | `%01000000` |  | Y flip |
| `OAMF_XFLIP` | `%00100000` |  | X flip |
| `OAMF_PAL0` | `%00000000` |  | Palette number; 0,1 (DMG) |
| `OAMF_PAL1` | `%00010000` |  | Palette number; 0,1 (DMG) |
| `OAMF_BANK0` | `%00000000` |  | Bank number; 0,1 (GBC) |
| `OAMF_BANK1` | `%00001000` |  | Bank number; 0,1 (GBC) |
| `OAMF_PALMASK` | `%00000111` |  | Palette (GBC) |
| `OAMB_PRI` | `7` |  | Priority |
| `OAMB_YFLIP` | `6` |  | Y flip |
| `OAMB_XFLIP` | `5` |  | X flip |
| `OAMB_PAL1` | `4` |  | Palette number; 0,1 (DMG) |
| `OAMB_BANK1` | `3` |  | Bank number; 0,1 (GBC) |
| `IEF_LCDC` | `%00000010` |  | LCDC (see STAT) |
| `_VRAM8000` | `_VRAM` |  |  |
| `_VRAM8800` | `_VRAM+$800` |  |  |
| `_VRAM9000` | `_VRAM+$1000` |  |  |
| `CART_SRAM_2KB` | `1` |  | 1 incomplete bank |
