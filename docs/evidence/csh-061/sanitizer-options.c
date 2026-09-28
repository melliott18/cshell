/* Unequal-ID exec strips sanitizer environment options. Keep the same Linux
 * leak-scan exclusion and halt-on-error settings in this diagnostic build. */
const char *__asan_default_options(void)
{
    return "halt_on_error=1:detect_leaks=0";
}
const char *__ubsan_default_options(void)
{
    return "halt_on_error=1";
}
