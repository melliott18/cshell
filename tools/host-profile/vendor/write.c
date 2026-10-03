/*-
 * CSH-077 portable standalone adaptation; see ../README.md for provenance.
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Copyright (c) 1989, 1993
 *	The Regents of the University of California.  All rights reserved.
 *
 * This code is derived from software contributed to Berkeley by
 * Jef Poskanzer and Craig Leres of the Lawrence Berkeley Laboratory.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the University nor the names of its contributors
 *    may be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 */

#include <sys/param.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/time.h>

#include <fcntl.h>
#include <time.h>
#include <ctype.h>
#include <err.h>
#include <errno.h>
#include <locale.h>
#include <limits.h>
#include <paths.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <utmpx.h>
#include <wchar.h>
#include <wctype.h>

static FILE *terminal_output;
static int recipient_fd = -1;

void done(int);
void do_write(int, char *, char *, const char *);
static void usage(void);
int term_chk(int, char *, int *, time_t *, int);
void wr_putwc(wchar_t c);
void search_utmp(int, char *, char *, char *, uid_t);
int utmp_chk(char *, char *);

int
main(int argc, char **argv)
{
	struct passwd *pwd;
	time_t atime;
	uid_t myuid;
	int msgsok, myttyfd;
	char tty[MAXPATHLEN], *mytty;
	const char *login;
	int devfd;

	(void)setlocale(LC_ALL, "");

	devfd = open(_PATH_DEV, O_RDONLY);
	if (devfd < 0)
		err(1, "open(/dev)");

	/* Preserve upstream login-name selection before opening the recipient. */
	myuid = getuid();
	if ((login = getlogin()) == NULL) {
		if ((pwd = getpwuid(myuid)))
			login = pwd->pw_name;
		else
			login = "???";
	}

	while (getopt(argc, argv, "") != -1)
		usage();
	argc -= optind;
	argv += optind;

	/* check that sender has write enabled */
	if (isatty(fileno(stdin)))
		myttyfd = fileno(stdin);
	else if (isatty(fileno(stdout)))
		myttyfd = fileno(stdout);
	else if (isatty(fileno(stderr)))
		myttyfd = fileno(stderr);
	else
		errx(1, "can't find your tty");
	if (!(mytty = ttyname(myttyfd)))
		errx(1, "can't find your tty's name");
	if (!strncmp(mytty, _PATH_DEV, strlen(_PATH_DEV)))
		mytty += strlen(_PATH_DEV);
	if (term_chk(devfd, mytty, &msgsok, &atime, 1))
		exit(1);
	if (!msgsok)
		errx(1, "you have write permission turned off");

	/* check args */
	switch (argc) {
	case 1:
		search_utmp(devfd, argv[0], tty, mytty, myuid);
		do_write(devfd, tty, mytty, login);
		break;
	case 2:
		if (!strncmp(argv[1], _PATH_DEV, strlen(_PATH_DEV)))
			argv[1] += strlen(_PATH_DEV);
		if (utmp_chk(argv[0], argv[1]))
			errx(1, "%s is not logged in on %s", argv[0], argv[1]);
		if (term_chk(devfd, argv[1], &msgsok, &atime, 1))
			exit(1);
		if (myuid && !msgsok)
			errx(1, "%s has messages disabled on %s", argv[0], argv[1]);
		do_write(devfd, argv[1], mytty, login);
		break;
	default:
		usage();
	}
	done(0);
	return (0);
}

static void
usage(void)
{
	(void)fprintf(stderr, "usage: write user [tty]\n");
	exit(1);
}

/*
 * utmp_chk - checks that the given user is actually logged in on
 *     the given tty
 */
int
utmp_chk(char *user, char *tty)
{
	struct utmpx *u;

	setutxent();
	while ((u = getutxent()) != NULL)
		if (u->ut_type == USER_PROCESS &&
		    strlen(user) <= sizeof(u->ut_user) &&
		    strlen(tty) <= sizeof(u->ut_line) &&
		    strncmp(user, u->ut_user, sizeof(u->ut_user)) == 0 &&
		    strncmp(tty, u->ut_line, sizeof(u->ut_line)) == 0) {
			endutxent();
			return(0);
		}
	endutxent();
	return(1);
}

/*
 * search_utmp - search utmp for the "best" terminal to write to
 *
 * Ignores terminals with messages disabled, and of the rest, returns
 * the one with the most recent access time.  Returns as value the number
 * of the user's terminals with messages enabled, or -1 if the user is
 * not logged in at all.
 *
 * Special case for writing to yourself - ignore the terminal you're
 * writing from, unless that's the only terminal with messages enabled.
 */
void
search_utmp(int devfd, char *user, char *tty, char *mytty, uid_t myuid)
{
	struct utmpx *u;
	char line[sizeof(u->ut_line) + 1];
	time_t bestatime, atime;
	int nloggedttys, nttys, msgsok, user_is_me;

	nloggedttys = nttys = 0;
	bestatime = 0;
	user_is_me = 0;
	setutxent();

	while ((u = getutxent()) != NULL)
		if (u->ut_type == USER_PROCESS &&
		    (strlen(user) <= sizeof(u->ut_user) &&
		    strncmp(user, u->ut_user, sizeof(u->ut_user)) == 0)) {
			memcpy(line, u->ut_line, sizeof(u->ut_line));
			line[sizeof(u->ut_line)] = '\0';
			++nloggedttys;
			if (term_chk(devfd, line, &msgsok, &atime, 0))
				continue;	/* bad term? skip */
			if (myuid && !msgsok)
				continue;	/* skip ttys with msgs off */
			if (strcmp(line, mytty) == 0) {
				user_is_me = 1;
				continue;	/* don't write to yourself */
			}
			++nttys;
			if (nttys == 1 || atime > bestatime) {
				bestatime = atime;
				(void)snprintf(tty, MAXPATHLEN, "%.*s",
				    (int)sizeof(u->ut_line), u->ut_line);
			}
		}
	endutxent();

	if (nloggedttys == 0)
		errx(1, "%s is not logged in", user);
	if (nttys == 0) {
		if (user_is_me) {		/* ok, so write to yourself! */
			(void)snprintf(tty, MAXPATHLEN, "%s", mytty);
			return;
		}
		errx(1, "%s has messages disabled", user);
	} else if (nloggedttys > 1) {
		if (printf("%s is logged in more than once; writing to %s\n", user, tty) < 0 || fflush(stdout) == EOF)
			err(1, "selection output");
	}
}

/*
 * term_chk - check that a terminal exists, and get the message bit
 *     and the access time
 */
int
term_chk(int devfd, char *tty, int *msgsokP, time_t *atimeP, int showerror)
{
	struct stat s;

	/* A session record is data, never permission to traverse outside /dev. */
	if (!*tty || *tty == '/' || !strcmp(tty, "..") ||
	    !strncmp(tty, "../", 3) || strstr(tty, "/../") ||
	    (strlen(tty) >= 3 && !strcmp(tty + strlen(tty) - 3, "/.."))) {
		if (showerror)
			warnx("invalid terminal name");
		return (1);
	}
	if (fstatat(devfd, tty, &s, AT_SYMLINK_NOFOLLOW) < 0 || !S_ISCHR(s.st_mode)) {
		if (showerror)
			warn("%s%s", _PATH_DEV, tty);
		return(1);
	}
	*msgsokP = (s.st_mode & S_IWGRP) != 0;	/* group write bit */
	*atimeP = s.st_atime;
	return(0);
}

/*
 * do_write - actually make the connection
 */
void
do_write(int devfd, char *tty, char *mytty, const char *login)
{
	char date[128];
	time_t now;
	struct tm local;
	struct stat recipient;
	struct sigaction action;
	wint_t c;
	int fd, sender, flags;

	/* The kernel still enforces the caller's credentials. No setgid install. */
	fd = openat(devfd, tty, O_WRONLY | O_NOCTTY | O_NONBLOCK | O_NOFOLLOW);
	if (fd < 0)
		err(1, "openat(%s%s)", _PATH_DEV, tty);
	if (fstat(fd, &recipient) < 0 || !isatty(fd))
		errx(1, "recipient is not a terminal");
	if (getuid() && !(recipient.st_mode & S_IWGRP))
		errx(1, "recipient has messages disabled");
	flags = fcntl(fd, F_GETFL);
	if (flags < 0 || fcntl(fd, F_SETFL, flags & ~O_NONBLOCK) < 0)
		err(1, "recipient descriptor");
	sender = openat(devfd, mytty, O_WRONLY | O_NOCTTY | O_NONBLOCK | O_NOFOLLOW);
	if (sender < 0 || !isatty(sender))
		errx(1, "cannot alert sender terminal");

	terminal_output = fdopen(fd, "w");
	if (terminal_output == NULL)
		err(1, "recipient output");
	recipient_fd = fd;
	/* Keep byte orientation for greetings; encode wide input with wcrtomb.
	 * Unbuffered output lets the async-safe SIGINT handler append EOT. */
	if (setvbuf(terminal_output, NULL, _IONBF, 0) != 0)
		errx(1, "cannot configure recipient output");
	memset(&action, 0, sizeof(action));
	action.sa_handler = done;
	sigemptyset(&action.sa_mask);
	if (sigaction(SIGINT, &action, NULL) < 0)
		err(1, "SIGINT");
	now = time(NULL);
	if (localtime_r(&now, &local) == NULL ||
	    !strftime(date, sizeof(date), "%Y-%m-%d %H:%M:%S", &local))
		errx(1, "message time");
	if (fprintf(terminal_output, "Message from %s (%s) [%s] ...\n", login, mytty, date) < 0)
		err(1, "greeting");
	if (write(sender, "\a\a", 2) != 2)
		err(1, "sender alerts");
	close(sender);

	while ((c = fgetwc(stdin)) != WEOF)
		wr_putwc((wchar_t)c);
	if (ferror(stdin))
		err(1, "message input");
}

/* write and _exit are async-signal-safe, unlike the upstream printf/exit.
 * Recipient output is unbuffered; no pending stdio bytes can follow the EOT marker. */
void
done(int signo)
{
	const char *message = "EOT\n";
	size_t left = 4;
	(void)signo;
	while (left) {
		ssize_t n = write(recipient_fd, message, left);
		if (n < 0 && errno == EINTR)
			continue;
		if (n <= 0) {
			/* Best effort only: the EOT failure already determines exit 1. */
			ssize_t diagnostic_bytes = write(STDERR_FILENO, "write: EOT output failed\n",
			    sizeof("write: EOT output failed\n") - 1);
			(void)diagnostic_bytes;
			_exit(1);
		}
		message += n;
		left -= (size_t)n;
	}
	_exit(0);
}

/* Preserve print/space/bell, including newlines, in the selected LC_CTYPE.
 * Other valid nonprinting characters use the documented FreeBSD hex policy. */
void
wr_putwc(wchar_t c)
{
	static mbstate_t state;
	char bytes[MB_LEN_MAX];
	size_t count;
	if (c == L'\a' || iswprint(c) || iswspace(c)) {
		count = wcrtomb(bytes, c, &state);
		if (count == (size_t)-1 || fwrite(bytes, 1, count, terminal_output) != count)
			err(1, "message output");
	} else if (fprintf(terminal_output, "<0x%X>", (unsigned)c) < 0) {
		err(1, "message output");
	}
}
