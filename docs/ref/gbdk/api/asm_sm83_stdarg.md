# `asm/sm83/stdarg.h` (GBDK-2020, gb target)

Source: tools/gbdk/include/asm/sm83/stdarg.h (gbdk-4.5.0, https://github.com/gbdk-2020/gbdk-2020); licence: GPLv2 with linking exception (tools/gbdk/licenses).



## Header

```c
#ifndef ASM_SM83_STDARG_INCLUDE
#define ASM_SM83_STDARG_INCLUDE

/* sdcc pushes right to left with the real sizes, not cast up
   to an int.
   so printf(int, char, long)
   results in push long, push char, push int
   On the z80 the stack grows down, so the things seem to be in
   the correct order.
 */

typedef unsigned char * va_list;
#define va_start(list, last)	list = (unsigned char *)&last + sizeof(last)
#define va_arg(list, type)	*((type *)((list += sizeof(type)) - sizeof(type)))

#define va_end(list)

#endif
```
