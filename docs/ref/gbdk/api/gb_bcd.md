# `gb/bcd.h` (GBDK-2020, gb target)

Source: tools/gbdk/include/gb/bcd.h (gbdk-4.5.0, https://github.com/gbdk-2020/gbdk-2020); licence: GPLv2 with linking exception (tools/gbdk/licenses).

Support for working with BCD (Binary Coded Decimal) See the example BCD project for additional details.

| Name | Summary |
|---|---|
| `MAKE_BCD` | Converts an integer value into BCD format A maximum of 8 digits may be used |
| `uint2bcd` | Converts integer __i__ into BCD format (Binary Coded Decimal) i Numeric value to convert value Pointer to a BCD variable to store the conver |
| `bcd_sub` | Subtracts two numbers in BCD format: __sour__ -= __value__ sour Pointer to a BCD value to subtract from (and where the result is stored) val |

## Header

```c
#ifndef __BCD_H_INCLUDE
#define __BCD_H_INCLUDE

#include <types.h>
#include <stdint.h>

/** @file bcd.h
    Support for working with BCD (Binary Coded Decimal)

    See the example BCD project for additional details.
*/

// macro for creating BCD constants
#define BCD_HEX(v) ((BCD)(v))

/** Converts an integer value into BCD format

    A maximum of 8 digits may be used
*/
#define MAKE_BCD(v) BCD_HEX(0x ## v)

typedef uint32_t BCD;

/** Converts integer __i__ into BCD format (Binary Coded Decimal)
    @param i      Numeric value to convert
    @param value  Pointer to a BCD variable to store the converted result
*/
void uint2bcd(uint16_t i, BCD * value) OLDCALL;

/** Adds two numbers in BCD format: __sour__ += __value__
    @param sour   Pointer to a BCD value to add to (and where the result is stored)
    @param value  Pointer to the BCD value to add to __sour__
*/
void bcd_add(BCD * sour, const BCD * value) OLDCALL;

/** Subtracts two numbers in BCD format: __sour__ -= __value__
    @param sour   Pointer to a BCD value to subtract from (and where the result is stored)
    @param value  Pointer to the BCD value to subtract from __sour__
*/
void bcd_sub(BCD * sour, const BCD * value) OLDCALL;

/** Convert a BCD number into an asciiz (null terminated) string and return the length
    @param bcd          Pointer to BCD value to convert
    @param tile_offset  Optional per-character offset value to add (use 0 for none)
    @param buffer       Buffer to store the result in

    Returns: Length in characters (always 8)

    __buffer__ should be large enough to store the converted string
    (9 bytes: 8 characters + 1 for terminator)

    There are a couple different ways to use __tile_offset__.
    For example:
    \li It can be the Index of the Font Tile '0'  in VRAM to
    allow the buffer to be used directly with @ref set_bkg_tiles.
    \li It can also be set to the ascii value for character '0'
    so that the buffer is a normal string that can be passed to @ref printf.
*/
uint8_t bcd2text(const BCD * bcd, uint8_t tile_offset, uint8_t * buffer) OLDCALL;

#endif
```
