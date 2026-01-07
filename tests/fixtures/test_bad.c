#include <stdio.h>

int debug_mode;

int a, b;

void too_many_args(int a, int b, int c, int d, int e)
{
    printf("Too many args\n");
}

void very_long_function(void)
{
    int x = 1;
    int y = 2;
    int z = 3;
    int w = 4;
    x = x + 1;
    y = y + 1;
    z = z + 1;
    w = w + 1;
    x = x + 2;
    y = y + 2;
    z = z + 2;
    w = w + 2;
    x = x + 3;
    y = y + 3;
    z = z + 3;
    w = w + 3;
    x = x + 4;
    y = y + 4;
    z = z + 4;
    w = w + 4;
    x = x + 5;
    y = y + 5;
    z = z + 5;
    w = w + 5;
    x = x + 6;
    y = y + 6;
    z = z + 6;
    w = w + 6;
    x = x + 7;
    y = y + 7;
    z = z + 7;
    w = w + 7;
    x = x + 8;
    y = y + 8;
    z = z + 8;
    w = w + 8;
    x = x + 9;
    y = y + 9;
    z = z + 9;
    w = w + 9;
    printf("Done: %d %d %d %d\n", x, y, z, w);
}

void has_vla(int n)
{
    int arr[n];
    arr[0] = 0;
}

int main(void)
{
    return 0;
}
