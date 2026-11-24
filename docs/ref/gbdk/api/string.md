# `string.h` (GBDK-2020, gb target)

Source: tools/gbdk/include/string.h (gbdk-4.5.0, https://github.com/gbdk-2020/gbdk-2020); licence: GPLv2 with linking exception (tools/gbdk/licenses).

Generic string functions.

## Header

```c
/** @file string.h
    Generic string functions.
 */
#ifndef STD_STRING_INCLUDE
#define STD_STRING_INCLUDE

#if defined(__PORT_sm83)
  #include <asm/sm83/string.h>
#elif defined(__PORT_z80)
  #include <asm/z80/string.h>
#elif defined(__PORT_mos6502)
  #include <asm/mos6502/string.h>
#else
  #error Unrecognized port
#endif

#endif
```
