#ifndef CHECK_H
#define CHECK_H
#include <stdio.h>
extern int g_fail, g_checks;
#define CHECK(c) do { g_checks++; if (!(c)) { g_fail++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)
void run_nor_tests(void);
void run_layout_tests(void);
void run_library_tests(void);
void run_ecp5_tests(void);
#endif
