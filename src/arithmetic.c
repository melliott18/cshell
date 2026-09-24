#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cshell/arithmetic.h"
#include "cshell/state.h"

enum token {
    TOK_END, TOK_BAD, TOK_NUMBER, TOK_NAME, TOK_LPAREN, TOK_RPAREN,
    TOK_COMMA, TOK_ASSIGN, TOK_MUL_ASSIGN, TOK_DIV_ASSIGN, TOK_MOD_ASSIGN,
    TOK_ADD_ASSIGN, TOK_SUB_ASSIGN, TOK_SHL_ASSIGN, TOK_SHR_ASSIGN,
    TOK_AND_ASSIGN, TOK_XOR_ASSIGN, TOK_OR_ASSIGN, TOK_QUESTION, TOK_COLON,
    TOK_OR, TOK_AND, TOK_BIT_OR, TOK_BIT_XOR, TOK_BIT_AND, TOK_EQ, TOK_NE,
    TOK_LT, TOK_LE, TOK_GT, TOK_GE, TOK_SHL, TOK_SHR, TOK_ADD, TOK_SUB,
    TOK_MUL, TOK_DIV, TOK_MOD, TOK_NOT, TOK_INV
};

struct parser {
    const char *next;
    const char *start;
    size_t length;
    enum token token;
    enum csh_arith_result error;
    struct csh_state *state;
    unsigned options;
    unsigned depth;
    int incomplete;
};

/* An unresolved variable is an lvalue; reading is delayed until needed so that
 * x=1 does not inspect x's former value. A literal magnitude just above LONG_MAX
 * is also delayed, permitting the spelling of LONG_MIN after unary minus. */
struct value {
    long number;
    const char *name;
    size_t length;
    unsigned high;
};

static int name_start(unsigned char byte)
{
    return (byte >= 'a' && byte <= 'z') || (byte >= 'A' && byte <= 'Z') ||
        byte == '_';
}

static int digit(unsigned char byte)
{
    return byte >= '0' && byte <= '9';
}

static int space(unsigned char byte)
{
    return byte == ' ' || byte == '\t' || byte == '\n' || byte == '\r' ||
        byte == '\v' || byte == '\f';
}

static int digit_value(unsigned char byte)
{
    if (digit(byte))
        return byte - '0';
    if (byte >= 'a' && byte <= 'f')
        return byte - 'a' + 10;
    if (byte >= 'A' && byte <= 'F')
        return byte - 'A' + 10;
    return -1;
}

static int literal(const char *text, size_t length, struct value *out)
{
    unsigned base = 10;
    unsigned long magnitude = 0;
    unsigned long limit = (unsigned long)LONG_MAX + 1UL;
    size_t index = 0;
    int too_large = 0;
    if (length == 0)
        return 0;
    if (text[0] == '0') {
        base = 8;
        if (length >= 2 && (text[1] == 'x' || text[1] == 'X')) {
            base = 16;
            index = 2;
            if (index == length)
                return 0;
        }
    }
    for (; index < length; ++index) {
        int number = digit_value((unsigned char)text[index]);
        if (number < 0 || (unsigned)number >= base)
            return 0;
        if (!too_large) {
            if (magnitude > (limit - (unsigned)number) / base)
                too_large = 1;
            else
                magnitude = magnitude * base + (unsigned)number;
        }
    }
    out->high = too_large ? 2u : magnitude > (unsigned long)LONG_MAX;
    out->number = out->high ? 0 : (long)magnitude;
    return 1;
}

static void next_token(struct parser *parser)
{
    static const struct {
        const char *text;
        enum token token;
    } operators[] = {
        {"<<=", TOK_SHL_ASSIGN}, {">>=", TOK_SHR_ASSIGN},
        {"*=", TOK_MUL_ASSIGN}, {"/=", TOK_DIV_ASSIGN},
        {"%=", TOK_MOD_ASSIGN}, {"+=", TOK_ADD_ASSIGN},
        {"-=", TOK_SUB_ASSIGN}, {"&=", TOK_AND_ASSIGN},
        {"^=", TOK_XOR_ASSIGN}, {"|=", TOK_OR_ASSIGN},
        {"||", TOK_OR}, {"&&", TOK_AND}, {"==", TOK_EQ},
        {"!=", TOK_NE}, {"<=", TOK_LE}, {">=", TOK_GE},
        {"<<", TOK_SHL}, {">>", TOK_SHR}, {"++", TOK_BAD}, {"--", TOK_BAD},
        {"(", TOK_LPAREN}, {")", TOK_RPAREN}, {",", TOK_COMMA},
        {"=", TOK_ASSIGN}, {"?", TOK_QUESTION}, {":", TOK_COLON},
        {"|", TOK_BIT_OR}, {"^", TOK_BIT_XOR}, {"&", TOK_BIT_AND},
        {"<", TOK_LT}, {">", TOK_GT}, {"+", TOK_ADD}, {"-", TOK_SUB},
        {"*", TOK_MUL}, {"/", TOK_DIV}, {"%", TOK_MOD},
        {"!", TOK_NOT}, {"~", TOK_INV}
    };
    size_t index;
    const char *text = parser->next;
    while (space((unsigned char)*text))
        ++text;
    parser->start = text;
    parser->length = 0;
    if (*text == '\0') {
        parser->token = TOK_END;
        parser->next = text;
        return;
    }
    if (name_start((unsigned char)*text) || digit((unsigned char)*text)) {
        parser->token = digit((unsigned char)*text) ? TOK_NUMBER : TOK_NAME;
        do {
            ++text;
        } while (name_start((unsigned char)*text) || digit((unsigned char)*text));
        parser->length = (size_t)(text - parser->start);
        parser->next = text;
        return;
    }
    for (index = 0; index < sizeof(operators) / sizeof(operators[0]); ++index) {
        size_t length = strlen(operators[index].text);
        if (strncmp(text, operators[index].text, length) == 0) {
            parser->token = operators[index].token;
            parser->length = length;
            parser->next = text + length;
            return;
        }
    }
    parser->token = TOK_BAD;
    parser->length = 1;
    parser->next = text + 1;
}

static char *copy_name(struct parser *parser, struct value value)
{
    char *name = malloc(value.length + 1);
    if (name == NULL) {
        parser->error = CSH_ARITH_NOMEM;
        return NULL;
    }
    memcpy(name, value.name, value.length);
    name[value.length] = '\0';
    return name;
}

static long read_value(struct parser *parser, struct value value, int execute)
{
    struct csh_variable_view view;
    const char *text;
    char *name;
    int negative = 0;
    if (!execute || parser->error != CSH_ARITH_OK)
        return 0;
    if (value.name != NULL) {
        name = copy_name(parser, value);
        if (name == NULL)
            return 0;
        (void)csh_state_get_variable(parser->state, name, &view);
        free(name);
        text = view.value;
        if (text == NULL) {
            if (parser->options & CSH_OPT_NOUNSET)
                parser->error = CSH_ARITH_SYNTAX;
            return 0;
        }
        if (*text == '\0')
            return 0;
        if (*text == '-' || *text == '+') {
            negative = *text == '-';
            ++text;
        }
        value = (struct value){0};
        if (!literal(text, strlen(text), &value)) {
            parser->error = CSH_ARITH_SYNTAX;
            return 0;
        }
        if (negative && value.high == 1)
            return LONG_MIN;
        if (negative)
            value.number = -value.number;
    }
    if (value.high != 0) {
        parser->error = CSH_ARITH_RANGE;
        return 0;
    }
    return value.number;
}

static void assign(struct parser *parser, struct value target, long number)
{
    char buffer[sizeof(long) * CHAR_BIT + 2];
    char *name = copy_name(parser, target);
    enum csh_state_result result;
    if (name == NULL)
        return;
    (void)snprintf(buffer, sizeof(buffer), "%ld", number);
    result = csh_state_set_variable(parser->state, name, buffer);
    if (result == CSH_STATE_OK && (parser->options & CSH_OPT_ALLEXPORT))
        result = csh_state_update_attributes(parser->state, name, CSH_VAR_EXPORT, 0);
    free(name);
    if (result == CSH_STATE_NOMEM)
        parser->error = CSH_ARITH_NOMEM;
    else if (result == CSH_STATE_READONLY)
        parser->error = CSH_ARITH_READONLY;
    else if (result != CSH_STATE_OK)
        parser->error = CSH_ARITH_SYNTAX;
}

static long operation(struct parser *parser, enum token token, long left, long right)
{
    switch (token) {
    case TOK_ADD:
        if ((right > 0 && left > LONG_MAX - right) ||
            (right < 0 && left < LONG_MIN - right))
            break;
        return left + right;
    case TOK_SUB:
        if ((right < 0 && left > LONG_MAX + right) ||
            (right > 0 && left < LONG_MIN + right))
            break;
        return left - right;
    case TOK_MUL:
        if (left > 0 ? (right > 0 ? left > LONG_MAX / right :
                right < LONG_MIN / left) :
            (left < 0 && (right > 0 ? left < LONG_MIN / right :
                right < 0 && left < LONG_MAX / right)))
            break;
        return left * right;
    case TOK_DIV:
    case TOK_MOD:
        if (right == 0 || (left == LONG_MIN && right == -1))
            break;
        return token == TOK_DIV ? left / right : left % right;
    case TOK_SHL:
    case TOK_SHR:
        if (right < 0 || (unsigned long)right >= sizeof(long) * CHAR_BIT)
            break;
        if (token == TOK_SHL) {
            if (left < 0 || left > (LONG_MAX >> right))
                break;
            return left << right;
        }
        /* Avoid implementation-defined signed right shift for negative values. */
        return left >= 0 ? left >> right : -1 - ((-1 - left) >> right);
    case TOK_LT: return left < right;
    case TOK_LE: return left <= right;
    case TOK_GT: return left > right;
    case TOK_GE: return left >= right;
    case TOK_EQ: return left == right;
    case TOK_NE: return left != right;
    case TOK_BIT_AND: return left & right;
    case TOK_BIT_XOR: return left ^ right;
    case TOK_BIT_OR: return left | right;
    case TOK_AND: return left != 0 && right != 0;
    case TOK_OR: return left != 0 || right != 0;
    case TOK_COMMA: return right;
    default: parser->error = CSH_ARITH_SYNTAX; return 0;
    }
    parser->error = CSH_ARITH_RANGE;
    return 0;
}

static int precedence(enum token token)
{
    switch (token) {
    case TOK_COMMA: return 1;
    case TOK_ASSIGN: case TOK_MUL_ASSIGN: case TOK_DIV_ASSIGN:
    case TOK_MOD_ASSIGN: case TOK_ADD_ASSIGN: case TOK_SUB_ASSIGN:
    case TOK_SHL_ASSIGN: case TOK_SHR_ASSIGN: case TOK_AND_ASSIGN:
    case TOK_XOR_ASSIGN: case TOK_OR_ASSIGN: return 2;
    case TOK_QUESTION: return 3;
    case TOK_OR: return 4;
    case TOK_AND: return 5;
    case TOK_BIT_OR: return 6;
    case TOK_BIT_XOR: return 7;
    case TOK_BIT_AND: return 8;
    case TOK_EQ: case TOK_NE: return 9;
    case TOK_LT: case TOK_LE: case TOK_GT: case TOK_GE: return 10;
    case TOK_SHL: case TOK_SHR: return 11;
    case TOK_ADD: case TOK_SUB: return 12;
    case TOK_MUL: case TOK_DIV: case TOK_MOD: return 13;
    default: return 0;
    }
}

static enum token assignment_operation(enum token token)
{
    switch (token) {
    case TOK_MUL_ASSIGN: return TOK_MUL;
    case TOK_DIV_ASSIGN: return TOK_DIV;
    case TOK_MOD_ASSIGN: return TOK_MOD;
    case TOK_ADD_ASSIGN: return TOK_ADD;
    case TOK_SUB_ASSIGN: return TOK_SUB;
    case TOK_SHL_ASSIGN: return TOK_SHL;
    case TOK_SHR_ASSIGN: return TOK_SHR;
    case TOK_AND_ASSIGN: return TOK_BIT_AND;
    case TOK_XOR_ASSIGN: return TOK_BIT_XOR;
    case TOK_OR_ASSIGN: return TOK_BIT_OR;
    default: return TOK_BAD;
    }
}

static struct value expression(struct parser *, int, int);

static struct value primary(struct parser *parser, int execute)
{
    struct value value = {0};
    enum token token = parser->token;
    if (token == TOK_NUMBER) {
        if (!literal(parser->start, parser->length, &value))
            parser->error = CSH_ARITH_SYNTAX;
        next_token(parser);
    } else if (token == TOK_NAME) {
        value.name = parser->start;
        value.length = parser->length;
        next_token(parser);
    } else if (token == TOK_LPAREN) {
        next_token(parser);
        value = expression(parser, 1, execute);
        if (parser->error == CSH_ARITH_OK) {
            if (parser->token != TOK_RPAREN) {
                parser->error = CSH_ARITH_SYNTAX;
                parser->incomplete = parser->token == TOK_END;
            } else
                next_token(parser);
        }
    } else if (token == TOK_ADD || token == TOK_SUB || token == TOK_NOT ||
        token == TOK_INV) {
        next_token(parser);
        value = expression(parser, 14, execute);
        if (execute && parser->error == CSH_ARITH_OK) {
            if (token == TOK_SUB && value.name == NULL && value.high == 1) {
                value.number = LONG_MIN;
            } else {
                long number = read_value(parser, value, execute);
                if (token == TOK_SUB && number == LONG_MIN)
                    parser->error = CSH_ARITH_RANGE;
                else if (token == TOK_SUB)
                    value.number = -number;
                else if (token == TOK_NOT)
                    value.number = !number;
                else if (token == TOK_INV)
                    value.number = ~number;
                else
                    value.number = number;
            }
        }
        value.name = NULL;
        value.high = 0;
    } else {
        parser->error = CSH_ARITH_SYNTAX;
        parser->incomplete = parser->token == TOK_END;
    }
    return value;
}

static struct value expression(struct parser *parser, int minimum, int execute)
{
    struct value left = {0};
    if (parser->error != CSH_ARITH_OK)
        return left;
    if (parser->depth == 128) {
        parser->error = CSH_ARITH_SYNTAX;
        return left;
    }
    ++parser->depth;
    left = primary(parser, execute);
    while (parser->error == CSH_ARITH_OK && precedence(parser->token) >= minimum) {
        enum token token = parser->token;
        int priority = precedence(token);
        int is_assignment = priority == 2;
        long lhs = 0;
        long rhs;
        struct value right;
        int right_execute = execute;
        next_token(parser);
        if (is_assignment && left.name == NULL) {
            parser->error = CSH_ARITH_SYNTAX;
            break;
        }
        if (token != TOK_ASSIGN)
            lhs = read_value(parser, left, execute);
        if (token == TOK_QUESTION) {
            struct value selected = expression(parser, 1, execute && lhs != 0);
            long yes = read_value(parser, selected, execute && lhs != 0);
            if (parser->error != CSH_ARITH_OK)
                break;
            if (parser->token != TOK_COLON) {
                parser->error = CSH_ARITH_SYNTAX;
                parser->incomplete = parser->token == TOK_END;
                break;
            }
            next_token(parser);
            selected = expression(parser, priority, execute && lhs == 0);
            rhs = read_value(parser, selected, execute && lhs == 0);
            left = (struct value){.number = lhs != 0 ? yes : rhs};
            continue;
        }
        if (token == TOK_AND && lhs == 0)
            right_execute = 0;
        if (token == TOK_OR && lhs != 0)
            right_execute = 0;
        right = expression(parser, priority + !is_assignment, right_execute);
        rhs = read_value(parser, right, right_execute);
        if (execute && parser->error == CSH_ARITH_OK) {
            long number;
            if (is_assignment) {
                number = token == TOK_ASSIGN ? rhs :
                    operation(parser, assignment_operation(token), lhs, rhs);
                if (parser->error == CSH_ARITH_OK)
                    assign(parser, left, number);
            } else {
                number = operation(parser, token, lhs, rhs);
            }
            left = (struct value){.number = number};
        } else {
            left = (struct value){0};
        }
    }
    --parser->depth;
    return left;
}

static enum csh_arith_result run(struct parser *parser, int execute, long *out)
{
    struct value result = {0};
    next_token(parser);
    if (parser->token != TOK_END)
        result = expression(parser, 1, execute);
    if (parser->error == CSH_ARITH_OK && parser->token != TOK_END)
        parser->error = CSH_ARITH_SYNTAX;
    if (parser->error == CSH_ARITH_OK) {
        long number = read_value(parser, result, execute);
        if (parser->error == CSH_ARITH_OK && out != NULL)
            *out = number;
    }
    return parser->error;
}

enum csh_arith_result csh_arith_probe(const char *text)
{
    struct parser parser = {0};
    if (text == NULL)
        return CSH_ARITH_SYNTAX;
    parser.next = text;
    return run(&parser, 0, NULL);
}

int csh_arith_probe_prefix(const char *text)
{
    struct parser parser = {0};
    if (text == NULL)
        return 0;
    parser.next = text;
    return run(&parser, 0, NULL) == CSH_ARITH_OK || parser.incomplete;
}

enum csh_arith_result csh_arith_eval(struct csh_state *state,
    const char *text, long *out)
{
    struct csh_state_checkpoint *checkpoint = NULL;
    struct csh_state_info info;
    struct parser parser = {0};
    char *copy;
    size_t length;
    enum csh_arith_result result;
    if (state == NULL || text == NULL || out == NULL)
        return CSH_ARITH_SYNTAX;
    length = strlen(text);
    if (length == SIZE_MAX)
        return CSH_ARITH_NOMEM;
    copy = malloc(length + 1);
    if (copy == NULL)
        return CSH_ARITH_NOMEM;
    memcpy(copy, text, length + 1);
    if (csh_state_save(state, &checkpoint) != CSH_STATE_OK) {
        free(copy);
        return CSH_ARITH_NOMEM;
    }
    (void)csh_state_get_info(state, &info);
    parser.next = copy;
    parser.state = state;
    parser.options = info.options;
    result = run(&parser, 1, out);
    free(copy);
    if (result != CSH_ARITH_OK)
        (void)csh_state_restore(state, &checkpoint);
    csh_state_checkpoint_destroy(checkpoint);
    return result;
}
