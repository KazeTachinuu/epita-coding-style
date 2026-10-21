
#include <stdio.h>
  #define X 1
int g1;
int g2, g3;
static int helper(){ return 0; }
int too_many(int a, int b, int c, int d, int e)
{
    int n = a;
    int arr[n];
    int x = 1, y = 2;
    for (x = 0; x < 3; x++);
    while (y) {}
    if (x) goto end;
    y = (int)3.5;
    x = (1, 2);
    asm("nop");
    /* bad
       comment */
end:
    return n + arr[0] + x + y + b + c + d + e;   
}
#if X
#endif
int f1(void){return 1;}
int f2(void) { return ??= 2; }


