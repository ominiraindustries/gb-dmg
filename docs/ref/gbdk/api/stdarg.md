# `stdarg.h` (GBDK-2020, gb target)

Source: tools/gbdk/include/stdarg.h (gbdk-4.5.0, https://github.com/gbdk-2020/gbdk-2020); licence: GPLv2 with linking exception (tools/gbdk/licenses).



## Header

```c
#ifndef STDARG_INCLUDE
#define STDARG_INCLUDE

#if defined(__PORT_sm83)
#include <asm/sm83/stdarg.h>
#elif defined(__PORT_z80)
#include <asm/z80/stdarg.h>
#elif defined(__PORT_mos6502)
#include <asm/mos6502/stdarg.h>
#endif

#endif
```
