#include <stdlib.h>
#include "sb_compat.h"

#ifdef _WIN32
intptr_t getline(char **lineptr, size_t *n, FILE *stream)
{
    size_t len = 0;
    int c;
    if (!lineptr || !n) return -1;
    if (!*lineptr || *n == 0) {
        *n = 128;
        *lineptr = malloc(*n);
        if (!*lineptr) return -1;
    }
    while ((c = fgetc(stream)) != EOF) {
        if (len + 2 > *n) {
            char *p = realloc(*lineptr, *n * 2);
            if (!p) return -1;
            *lineptr = p;
            *n *= 2;
        }
        (*lineptr)[len++] = (char)c;
        if (c == '\n') break;
    }
    if (len == 0) return -1;
    (*lineptr)[len] = 0;
    return (intptr_t)len;
}
#endif
