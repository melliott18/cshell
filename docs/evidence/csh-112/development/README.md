# Setup observations

The initial native `make -j4 cshell host-profile` compiled the shell and local
providers, then exited 2 because `gfind` was unavailable on the provisioning
PATH. Adding `/opt/homebrew/bin` did not supply it. The first validation attempt
was interrupted during harness tests after this prerequisite error was noticed;
its log is incomplete and is not a passing validation record.

The final run uses a local copy of the exact CSH-111 `gfind` executable with the
same SHA-256, and `/usr/local/bin` for the installed GNU coreutils. No provider
source, assertion, timeout or allowance was changed. `csh112-build.log`,
`csh112-provision.log` and `interrupted-validation.log` preserve those attempts.
