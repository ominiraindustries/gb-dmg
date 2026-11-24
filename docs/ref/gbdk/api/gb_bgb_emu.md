# `gb/bgb_emu.h` (GBDK-2020, gb target)

Source: tools/gbdk/include/gb/bgb_emu.h (gbdk-4.5.0, https://github.com/gbdk-2020/gbdk-2020); licence: GPLv2 with linking exception (tools/gbdk/licenses).

Shim for legacy use of @ref bgb_emu.h which has been migrated to @ref emu_debug.h See the `emu_debug` example 

## Header

```c
/** @file gb/bgb_emu.h

	Shim for legacy use of @ref bgb_emu.h which has been
    migrated to @ref emu_debug.h

    See the `emu_debug` example project included with gbdk.
*/
#ifndef __BGB_EMU_INCLUDE
#define __BGB_EMU_INCLUDE

#include <gbdk/emu_debug.h>

#endif
```
