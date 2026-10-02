/* Standalone checked-allocation compatibility for GNU gencat. */
static void *xmalloc(size_t n) {
    void *p = malloc(n); if (!p) error(EXIT_FAILURE, errno, "memory allocation"); return p;
}
static void *xcalloc(size_t n, size_t s) {
    void *p = calloc(n, s); if (!p) error(EXIT_FAILURE, errno, "memory allocation"); return p;
}
static void *xrealloc(void *p, size_t n) {
    p = realloc(p, n); if (!p) error(EXIT_FAILURE, errno, "memory allocation"); return p;
}
