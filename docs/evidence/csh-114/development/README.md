# Initial cleanup failure

`initial-harness.log` retains the first five focused harness tests. All 112
behavior assertions passed. The corruption test removed search permission
from the owned directory; verification failed as required, but cleanup also
failed with EACCES. The test's outer TemporaryDirectory cleanup removed it.

The repair adds a finalizer that restores access to the authored directory
using lstat, plus a sixth harness test proving it does not follow a replacement
symlink to another directory. Complete later platform runs validate the repair;
the original failed observation is not counted as a pass.
