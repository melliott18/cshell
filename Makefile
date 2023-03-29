# Makefile
# Mitchell Elliott
# CSE 134 asgn1

CFLAGS=-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2
CC=cc

myshell: lex.yy.o myshell.o
	cc -o myshell myshell.o lex.yy.o -lfl
myshell.o :	myshell.c	
	flex shell.l
	$(CC) $(CFLAGS) -c myshell.c
lex.yy.o: lex.yy.c
	$(CC) $(CFLAGS) -c lex.yy.c
lex.yy.c: shell.l
	flex shell.l
all	:
	flex shell.l
	$(CC) $(CFLAGS) -c lex.yy.c
	$(CC) $(CFLAGS) -c myshell.c
	cc -o myshell myshell.o lex.yy.o -lfl
clean   :
	rm -rf myshell myshell.o lex.yy.o lex.yy.c
