# CSH-072 extended filesystem evidence

This extension covers traversal, links, metadata, ustar archives and bounded
kernel I/O errors. Qualification is case-scoped; complete utility pages and
remaining contracts stay with CSH-079. See the [contract description](../../../host-filesystem-evidence.md).

Final run records and commands are collected after the focused native and hosted
Linux checks. `native-initial.json.gz` preserves the initial strict run: 148 pass,
20 fail. Sixteen failures are native find/pax contracts. Four were an incorrect
harness assumption that dd creates an output before detecting closed stdin;
the corrected fixture precreates an empty output and independently arms EBADF.
No provider expectation was relaxed.
