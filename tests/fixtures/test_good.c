#include "test_good.h"

#include <stdio.h>

static int g_counter = 0;

int add(int a, int b)
{
    return a + b;
}

void print_hello(void)
{
    printf("Hello, World!\n");
}

int main(void)
{
    g_counter = add(1, 2);
    print_hello();
    return 0;
}
