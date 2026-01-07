#ifndef TEST_EDGE_CASES_H
#define TEST_EDGE_CASES_H

/* Big enum in header */
enum status
{
    STATUS_OK,
    STATUS_ERROR,
    STATUS_PENDING,
    STATUS_CANCELLED,
    STATUS_TIMEOUT,
    STATUS_INVALID,
    STATUS_NOT_FOUND,
    STATUS_FORBIDDEN,
    STATUS_CONFLICT,
    STATUS_INTERNAL,
    STATUS_UNAVAILABLE,
    STATUS_UNKNOWN,
};

/* Struct in header */
struct point
{
    int x;
    int y;
    int z;
};

/* Union in header */
union data
{
    int i;
    float f;
    char c;
    void *ptr;
};

/* Function prototypes with void - correct */
int get_status(void);
void init_system(void);
struct point create_point(int x, int y, int z);

/* Function pointer typedef - allowed */
typedef int (*comparator_fn)(const void *, const void *);

/* Extern global with g_ prefix - correct */
extern int g_verbosity;

#endif /* ! TEST_EDGE_CASES_H */
