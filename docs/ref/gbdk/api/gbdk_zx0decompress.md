# `gbdk/zx0decompress.h` (GBDK-2020, gb target)

Source: tools/gbdk/include/gbdk/zx0decompress.h (gbdk-4.5.0, https://github.com/gbdk-2020/gbdk-2020); licence: GPLv2 with linking exception (tools/gbdk/licenses).



| Name | Summary |
|---|---|
| `zx0_decompress` | Decompress zx0 compressed data from sour into dest sour Pointer to source zx0 compressed data dest Pointer to destination buffer/address Wil |

## Header

```c
#ifndef __ZX0DECOMPRESS_H_INCLUDE
#define __ZX0DECOMPRESS_H_INCLUDE


/** Decompress zx0 compressed data from sour into dest

    @param sour   Pointer to source zx0 compressed data
    @param dest   Pointer to destination buffer/address

    Will decompress __all__ of it's data to destination without
    stopping until the end of compressed data is reached. It is
    not possible to set a limit, so ensure the destination buffer
    has sufficient space to avoid an overflow.

    Decompresses data which has been compressed with @ref utility_gbcompress "gbcompress" using the `--alg=zx0` argument.
*/
void zx0_decompress(void * sour, void * dest);


#endif
```
