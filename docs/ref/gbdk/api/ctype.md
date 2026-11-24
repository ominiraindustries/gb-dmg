# `ctype.h` (GBDK-2020, gb target)

Source: tools/gbdk/include/ctype.h (gbdk-4.5.0, https://github.com/gbdk-2020/gbdk-2020); licence: GPLv2 with linking exception (tools/gbdk/licenses).

Character type functions.

| Name | Summary |
|---|---|
| `isalpha` | Returns TRUE if the character __c__ is a letter (a-z, A-Z), otherwise FALSE c Character to test |
| `islower` | Returns TRUE if the character __c__ is a lowercase letter (a-z), otherwise FALSE c Character to test |
| `isspace` | Returns TRUE if the character __c__ is a space (' '), tab (\\t), or newline (\\n) character, otherwise FALSE c Character to test |
| `tolower` | Returns lowercase version of character __c__ if it is a letter (A-Z), otherwise it returns the input value unchanged |

## Header

```c
/** @file ctype.h
    Character type functions.
*/
#ifndef _CTYPE_H
#define _CTYPE_H

#include <types.h>
#include <stdbool.h>

/** Returns TRUE if the character __c__ is a letter (a-z, A-Z), otherwise FALSE
    @param c    Character to test
*/
bool isalpha(char c);

/** Returns TRUE if the character __c__ is an uppercase letter (A-Z), otherwise FALSE
    @param c    Character to test
*/
bool isupper(char c);

/** Returns TRUE if the character __c__ is a lowercase letter (a-z), otherwise FALSE
    @param c    Character to test
*/
bool islower(char c);

/** Returns TRUE if the character __c__ is a digit (0-9), otherwise FALSE
    @param c    Character to test
*/
bool isdigit(char c);

/** Returns TRUE if the character __c__ is a space (' '), tab (\\t), or newline (\\n) character, otherwise FALSE
    @param c    Character to test
*/
bool isspace(char c);

/** Returns uppercase version of character __c__  if it is a letter (a-z), otherwise it returns the input value unchanged.
    @param c    Character to test
*/
char toupper(char c);

/** Returns lowercase version of character __c__  if it is a letter (A-Z), otherwise it returns the input value unchanged.
    @param c    Character to test
*/
char tolower(char c);

#endif /* _CTYPE_H */
```
