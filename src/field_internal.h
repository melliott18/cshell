#ifndef CSHELL_FIELD_INTERNAL_H
#define CSHELL_FIELD_INTERNAL_H

#include "cshell/expand.h"

/* Copy one final field. The caller destroys all output after any failure. */
enum csh_expand_result csh_fields_append(struct csh_fields *out,
    const char *text, size_t length);

/* pattern protects quoted pattern characters and literal backslashes with
 * backslashes; expansion-produced unquoted backslashes retain matcher escape
 * semantics. Slashes remain separators even when escaped. raw is the literal
 * field returned when the pattern has no matches. Borrow all inputs. */
enum csh_expand_result csh_pathname_expand(const char *raw, const char *pattern,
    const struct csh_field_options *options, struct csh_fields *out);

#endif
