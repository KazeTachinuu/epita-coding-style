#include <stdio.h>

/* Big enum - should NOT trigger fun.length */
enum color
{
    COLOR_RED,
    COLOR_GREEN,
    COLOR_BLUE,
    COLOR_YELLOW,
    COLOR_ORANGE,
    COLOR_PURPLE,
    COLOR_PINK,
    COLOR_BROWN,
    COLOR_BLACK,
    COLOR_WHITE,
    COLOR_GRAY,
    COLOR_CYAN,
    COLOR_MAGENTA,
    COLOR_LIME,
    COLOR_MAROON,
    COLOR_NAVY,
    COLOR_OLIVE,
    COLOR_TEAL,
    COLOR_AQUA,
    COLOR_SILVER,
    COLOR_GOLD,
    COLOR_CORAL,
    COLOR_SALMON,
    COLOR_KHAKI,
    COLOR_PLUM,
    COLOR_ORCHID,
    COLOR_TAN,
    COLOR_PERU,
    COLOR_SIENNA,
    COLOR_CHOCOLATE,
    COLOR_TOMATO,
    COLOR_CRIMSON,
    COLOR_INDIGO,
    COLOR_VIOLET,
    COLOR_TURQUOISE,
    COLOR_LAVENDER,
    COLOR_BEIGE,
    COLOR_IVORY,
    COLOR_AZURE,
    COLOR_MINT,
    COLOR_ROSE,
    COLOR_RUBY,
    COLOR_EMERALD,
    COLOR_SAPPHIRE,
    COLOR_AMBER,
    COLOR_JADE,
    COLOR_COUNT,
};

/* Big struct - should NOT trigger fun.length */
struct big_config
{
    int field1;
    int field2;
    int field3;
    int field4;
    int field5;
    int field6;
    int field7;
    int field8;
    int field9;
    int field10;
    int field11;
    int field12;
    int field13;
    int field14;
    int field15;
    int field16;
    int field17;
    int field18;
    int field19;
    int field20;
    char *name;
    char *description;
    void *data;
};

/* Function with exactly 4 args - should pass */
int valid_args(int a, int b, int c, int d)
{
    return a + b + c + d;
}

/* Function with switch on enum - lines inside count */
const char *color_to_string(enum color c)
{
    switch (c)
    {
    case COLOR_RED:
        return "red";
    case COLOR_GREEN:
        return "green";
    case COLOR_BLUE:
        return "blue";
    case COLOR_YELLOW:
        return "yellow";
    case COLOR_ORANGE:
        return "orange";
    case COLOR_PURPLE:
        return "purple";
    case COLOR_PINK:
        return "pink";
    case COLOR_BROWN:
        return "brown";
    case COLOR_BLACK:
        return "black";
    case COLOR_WHITE:
        return "white";
    default:
        return "unknown";
    }
}

/* Static array initialization - should pass */
static int g_lookup_table[] = {
    0,  1,  2,  3,  4,  5,  6,  7,  8,  9,  10, 11, 12, 13, 14, 15, 16,
    17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
    34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
};

/* Function pointer typedef - allowed */
typedef void (*callback_fn)(int, void *);

/* Short function - should pass */
int get_count(void)
{
    return COLOR_COUNT;
}

int main(void)
{
    enum color c = COLOR_RED;
    printf("%s\n", color_to_string(c));
    return 0;
}
