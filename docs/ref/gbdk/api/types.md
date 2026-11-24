# `types.h` (GBDK-2020, gb target)

Source: tools/gbdk/include/types.h (gbdk-4.5.0, https://github.com/gbdk-2020/gbdk-2020); licence: GPLv2 with linking exception (tools/gbdk/licenses).

Basic types. Directly include the port specific file.

| Name | Summary |
|---|---|
| `FALSE` | A 'false' value. |
| `POINTER` | No longer used. |

## Header

```c
/** @file types.h
    Basic types.  
    Directly include the port specific file.
*/
#ifndef TYPES_INCLUDE
#define TYPES_INCLUDE

#include <asm/types.h>

#ifndef NULL
  #define NULL (void *)0
#endif

/** A 'false' value.
 */
#define FALSE 0
/** A 'true' value.
 */
#define TRUE 1

/** No longer used.
 */
typedef void * POINTER;

#endif
```
