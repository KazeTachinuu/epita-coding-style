#include <stdio.h>
#include "bad.hh"
#define SIZE 10
class my_class
{
public:
  my_class(int x);
  int &get();
  my_class& operator=(const my_class&);
};
namespace Foo {
int f(void)
{
  int *p = NULL;
  int* q = (int*)malloc(4);
  printf("%d", 1);
  throw 42;
  try { } catch (std::exception e) {}
  switch (1) { case 1 : break; }
  return 0;
}
}
enum Color { RED };
extern "C" int c_fn();
