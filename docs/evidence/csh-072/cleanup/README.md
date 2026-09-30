# CSH-072 Darwin cleanup follow-up

Repeated `/bin/ps -axo pid=,stat=` timeouts made otherwise successful pipe
runtime checks fail during zombie-group verification. The shared Darwin session
snapshot now uses libproc PID enumeration and short BSD metadata, retaining the
same session ownership, zombie exclusion, deadlines and snapshot size cap.

Final regression and integration evidence is collected after native and hosted
Linux validation. Historical ps timeouts remain in the original evidence.
