#ifndef CHECK_H
#define CHECK_H
#include <stdio.h>
extern int g_fail, g_checks;
#define CHECK(c) do { g_checks++; if (!(c)) { g_fail++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)
void run_bt820_tests(void);
#endif
