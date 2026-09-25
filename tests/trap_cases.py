"""Signal and trap behavior shared by the runtime's three input modes."""
import signal


def add_trap_cases(cross, helper):
    cross("traps: EXIT sees and preserves status",
          "trap 'printf \"exit:%s\\n\" \"$?\"' EXIT\nexit 7\n",
          status=7, stdout="exit:7\n")
    cross("traps: EXIT may replace status",
          "trap 'exit 9' EXIT\nexit 7\n", status=9)
    cross("traps: subshell EXIT may replace status",
          "(trap 'exit 9' EXIT; exit 7)\n", status=9)
    cross("traps: substitution EXIT may replace status",
          "value=$(trap 'exit 9' EXIT; exit 7)\n"
          "printf 'status:%s value:%s\\n' \"$?\" \"$value\"\n",
          stdout="status:9 value:\n")
    cross("traps: EXIT runs after errexit",
          "set -e\ntrap 'echo exit-action' EXIT\nfalse\necho never\n",
          status=1, stdout="exit-action\n")
    cross("traps: signal action and saved status",
          "trap 'printf \"caught:%s\\n\" \"$?\"; false' USR1\n"
          "kill -s USR1 $$\nprintf \"after:%s\\n\" \"$?\"\n",
          stdout="caught:0\nafter:0\n")
    cross("traps: listing and reset",
          "trap 'echo hello' INT\ntrap -p INT\ntrap - INT\ntrap -p INT\n",
          stdout="trap -- 'echo hello' INT\n")
    cross("traps: listing can be reinput",
          "trap \"echo 'quoted'\" USR1\nsaved=$(trap -p USR1)\n"
          "trap - USR1\neval \"$saved\"\nkill -s USR1 $$\n",
          stdout="quoted\n")
    cross("traps: ignored signal",
          "trap '' USR1\nkill -s USR1 $$\necho alive\n", stdout="alive\n")
    cross("traps: invalid condition continues",
          "trap 'echo never' CSH_INVALID\necho alive\n",
          stdout="alive\n", stderr="cshell: trap: invalid condition: CSH_INVALID\n")
    cross("traps: ignored signal reaches external utility",
          "trap '' INT\n/bin/sh -c 'kill -INT $$; echo survived'\n",
          stdout="survived\n")
    cross("traps: asynchronous command ignores INT despite parent action",
          "trap ':' INT\n/bin/sh -c 'kill -INT $$; echo survived' &\nwait\n",
          stdout="survived\n")
    cross("traps: caught hangup continues",
          "trap 'echo hangup' HUP\nkill -s HUP $$\necho alive\n",
          stdout="hangup\nalive\n")
    cross("traps: CHLD action does not reap children",
          "trap ':' CHLD\n/usr/bin/true\necho alive\n",
          stdout="alive\n")
    cross("traps: ignored CHLD retains wait ownership",
          "trap '' CHLD\n/usr/bin/true &\nwait\necho alive\n",
          stdout="alive\n")
    cross("traps: external signal dispositions",
          "trap 'echo caught' USR1\n"
          f"{helper} disposition USR1\n"
          "trap '' USR1\n"
          f"{helper} disposition USR1\n"
          "trap '' CHLD\n"
          f"{helper} disposition CHLD\n",
          stdout="default\nignored\nignored\n")
    cross("traps: function changes shell traps",
          "f() { trap 'echo function' USR1; }\nf\nkill -s USR1 $$\n",
          stdout="function\n")
    cross("traps: return in function action",
          "f() { trap 'return 9' USR1; kill -s USR1 $$; echo never; }\n"
          "f\nprintf 'status:%s\\n' \"$?\"\n",
          stdout="status:9\n")
    cross("traps: break in loop action",
          "while :; do trap 'break' USR1; kill -s USR1 $$; echo never; done\n"
          "echo after\n", stdout="after\n")
    cross("traps: eval changes shell traps",
          "eval \"trap 'echo eval' USR1\"\nkill -s USR1 $$\n",
          stdout="eval\n")
    cross("traps: subshell owns EXIT action",
          "trap 'echo parent' EXIT\n(trap 'echo child' EXIT)\necho after\n",
          stdout="child\nafter\nparent\n")
    cross("traps: caught action resets in subshell",
          "trap 'echo parent' USR1\n"
          "(/bin/sh -c 'kill -USR1 \"$PPID\"; sleep 0.1'; echo never)\n"
          "printf 'after:%s\\n' \"$?\"\n",
          stdout=f"after:{128 + signal.SIGUSR1}\n")
    cross("traps: substitution owns EXIT action",
          "trap 'echo parent' EXIT\nvalue=$(trap 'echo child' EXIT)\n"
          "printf 'value:%s\\n' \"$value\"\n",
          stdout="value:child\nparent\n")
    cross("traps: standalone substitution lists inherited actions",
          "trap 'echo saved' USR1\nvalue=$(trap -p USR1)\n"
          "printf 'value:%s\\n' \"$value\"\n",
          stdout="value:trap -- 'echo saved' USR1\n")
    cross("traps: foreground defers action",
          "trap 'echo trapped' USR1\n"
          "/bin/sh -c 'kill -USR1 \"$PPID\"; sleep 0.1; echo foreground'\n",
          stdout="foreground\ntrapped\n")
    cross("traps: pending signals use number order and coalesce",
          "trap 'echo first' USR1\ntrap 'echo second' USR2\n"
          "/bin/sh -c 'kill -USR2 \"$PPID\"; kill -USR1 \"$PPID\"; "
          "kill -USR1 \"$PPID\"; sleep 0.1; echo foreground'\n",
          stdout="foreground\nfirst\nsecond\n")
    cross("traps: wait interrupted before action",
          "trap 'printf \"trap:%s\\n\" \"$?\"' USR1\n"
          "/bin/sh -c 'sleep 0.1; kill -USR1 \"$1\"; sleep 0.2' sh \"$$\" &\n"
          "wait\nprintf \"wait:%s\\n\" \"$?\"\n",
          stdout=f"trap:{128 + signal.SIGUSR1}\nwait:{128 + signal.SIGUSR1}\n")
