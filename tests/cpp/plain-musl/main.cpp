#include <stdio.h>
#include <iostream>
#include <features.h>

using namespace std;

int main() {
  cout << "------\n";
#ifdef __GLIBC__
  cout << "Error: Linked against GLIBC?\n";
  return 1;
#else
  cout << "Hello Musl\n";
  return 0;
#endif
}
