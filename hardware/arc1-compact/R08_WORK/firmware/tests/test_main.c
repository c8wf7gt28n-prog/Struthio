#include "check.h"
int g_fail = 0, g_checks = 0;
int main(void)
{
    run_nor_tests();
    run_layout_tests();
    run_library_tests();
    printf("R08 firmware host tests: %d checks, %d failures\n", g_checks, g_fail);
    return g_fail ? 1 : 0;
}
