#include "cshell/character.h"

#include <locale.h>
#ifdef __APPLE__
#include <xlocale.h>
#endif
#include <wchar.h>

static locale_t startup;

int csh_character_startup(void)
{
    if (startup != (locale_t)0) return 0;
    startup = duplocale(uselocale((locale_t)0));
    return startup == (locale_t)0 ? -1 : 0;
}

void csh_character_shutdown(void)
{
    if (startup != (locale_t)0) freelocale(startup);
    startup = (locale_t)0;
}

size_t csh_character_length(const void *text, size_t length, int lexical, int final)
{
    mbstate_t state = {0};
    locale_t previous = (locale_t)0;
    size_t count;
    if (length == 0) return 0;
    /* ASCII bytes cannot start multibyte characters in supported encodings. */
    if (*(const unsigned char *)text < 0x80) return 1;
    if (lexical && startup != (locale_t)0) previous = uselocale(startup);
    count = mbrlen(text, length, &state);
    if (previous != (locale_t)0) (void)uselocale(previous);
    if (count == (size_t)-2 && !final) return 0;
    return count == (size_t)-1 || count == (size_t)-2 || count == 0 ? 1 : count;
}
