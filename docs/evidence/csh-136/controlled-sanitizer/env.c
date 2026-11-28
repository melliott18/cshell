#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
int main(void) { FILE *f=fopen("/proc/self/environ","r"); printf("ASAN_OPTIONS=%s proc_errno=%d\n",getenv("ASAN_OPTIONS"),f?0:errno); if(f) fclose(f); return 0; }
