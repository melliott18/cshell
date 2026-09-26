#include "cshell/character.h"
#include "cshell/quote.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

static int hexadecimal(unsigned char byte)
{
    if (byte >= '0' && byte <= '9')
        return byte - '0';
    if (byte >= 'a' && byte <= 'f')
        return byte - 'a' + 10;
    if (byte >= 'A' && byte <= 'F')
        return byte - 'A' + 10;
    return -1;
}

static int control(unsigned char byte)
{
    if (byte >= 'a' && byte <= 'z')
        return byte - 'a' + 1;
    if (byte >= 'A' && byte <= 'Z')
        return byte - 'A' + 1;
    switch (byte) {
    case '[': return 27;
    case '\\': return 28;
    case ']': return 29;
    case '^': return 30;
    case '_': return 31;
    case '?': return 127;
    default: return -1;
    }
}

enum csh_quote_result csh_quote_decode(const unsigned char *bytes, size_t length,
    char **out, size_t *out_length)
{
    char *result;
    size_t cursor = 0;
    size_t used = 0;

    if (out != NULL)
        *out = NULL;
    if (out_length != NULL)
        *out_length = 0;
    if (out == NULL || out_length == NULL || (bytes == NULL && length != 0))
        return CSH_QUOTE_INVALID;
    if (length == SIZE_MAX)
        return CSH_QUOTE_NOMEM;
    if (length != 0 && memchr(bytes, '\0', length) != NULL)
        return CSH_QUOTE_INVALID;
    /* No supported replacement is longer than its source escape. */
    result = malloc(length + 1);
    if (result == NULL)
        return CSH_QUOTE_NOMEM;

    while (cursor < length) {
        size_t width = csh_character_length(bytes + cursor, length - cursor, 1, 1);
        unsigned char byte;
        int check_control = 0;
        if (width > 1) {
            memcpy(result + used, bytes + cursor, width);
            used += width;
            cursor += width;
            continue;
        }
        byte = bytes[cursor++];

        if (byte == '\\' && cursor < length) {
            unsigned char escaped;
            unsigned int value;
            size_t digits;
            int digit;
            width = csh_character_length(bytes + cursor, length - cursor, 1, 1);
            if (width > 1) {
                result[used++] = '\\';
                memcpy(result + used, bytes + cursor, width);
                used += width;
                cursor += width;
                continue;
            }
            escaped = bytes[cursor++];

            switch (escaped) {
            case '"': byte = '"'; break;
            case '\'': byte = '\''; break;
            case '\\': byte = '\\'; break;
            case 'a': byte = '\a'; break;
            case 'b': byte = '\b'; break;
            case 'e': byte = 27; check_control = 1; break;
            case 'f': byte = '\f'; break;
            case 'n': byte = '\n'; break;
            case 'r': byte = '\r'; break;
            case 't': byte = '\t'; break;
            case 'v': byte = '\v'; break;
            case 'c':
                digit = cursor < length ? control(bytes[cursor]) : -1;
                if (digit >= 0 && (bytes[cursor] != '\\' ||
                    (length - cursor >= 2 && bytes[cursor + 1] == '\\'))) {
                    if (bytes[cursor] == '\\')
                        ++cursor;
                    ++cursor;
                    byte = (unsigned char)digit;
                    check_control = 1;
                    break;
                }
                result[used++] = '\\';
                byte = escaped;
                break;
            case 'x':
                value = 0;
                digits = 0;
                while (cursor < length && digits < 2 &&
                    (digit = hexadecimal(bytes[cursor])) >= 0) {
                    value = value * 16 + (unsigned int)digit;
                    ++cursor;
                    ++digits;
                }
                if (digits != 0) {
                    byte = (unsigned char)value;
                    break;
                }
                result[used++] = '\\';
                byte = escaped;
                break;
            default:
                if (escaped >= '0' && escaped <= '7') {
                    value = (unsigned int)(escaped - '0');
                    digits = 1;
                    while (cursor < length && digits < 3 &&
                        bytes[cursor] >= '0' && bytes[cursor] <= '7') {
                        value = value * 8 + (unsigned int)(bytes[cursor] - '0');
                        ++cursor;
                        ++digits;
                    }
                    byte = (unsigned char)(value % 256);
                } else {
                    result[used++] = '\\';
                    byte = escaped;
                }
                break;
            }
        }
        if (check_control && btowc(byte) == WEOF) {
            free(result);
            return CSH_QUOTE_INVALID;
        }
        if (byte == '\0')
            break;
        result[used++] = (char)byte;
    }
    result[used] = '\0';
    *out = result;
    *out_length = used;
    return CSH_QUOTE_OK;
}
