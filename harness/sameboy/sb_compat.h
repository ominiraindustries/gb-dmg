/* mingw-w64 has no POSIX getline(); SameBoy's Core uses it (debugger symbol files, stdin debugger). */
#pragma once
#include <stdio.h>
#include <stdint.h>
#ifdef _WIN32
intptr_t getline(char **lineptr, size_t *n, FILE *stream);
#endif
