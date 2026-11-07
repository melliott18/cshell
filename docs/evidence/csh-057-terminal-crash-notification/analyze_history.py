#!/usr/bin/env python3
"""Verify historical binaries/samples and call-site localization offline.

Only reads retained files. No commands, archive extraction, or process signals.
"""
import hashlib
import json
from pathlib import Path
import re
import struct
import tarfile
import uuid


HERE = Path(__file__).resolve().parent


def read_archive(path):
    with tarfile.open(path, "r:gz") as archive:
        return {member.name: archive.extractfile(member).read()
                for member in archive.getmembers() if member.isfile()}


def macho(data):
    """Read UUID, text mapping and symbols from the retained thin arm64 Mach-O."""
    header = struct.unpack_from("<8I", data)
    assert header[0] == 0xFEEDFACF and header[1] == 0x0100000C
    offset, result = 32, {}
    for _ in range(header[4]):
        command, size = struct.unpack_from("<II", data, offset)
        assert size >= 8 and offset + size <= len(data)
        if command == 0x1B:  # LC_UUID
            result["uuid"] = str(uuid.UUID(bytes=data[offset + 8:offset + 24])).upper()
        elif command == 0x19 and data[offset + 8:offset + 24].rstrip(b"\0") == b"__TEXT":
            result["text_vmaddr"], _, result["text_fileoff"] = struct.unpack_from("<QQQ", data, offset + 24)
        elif command == 2:  # LC_SYMTAB, nlist_64
            symoff, nsyms, stroff, strsize = struct.unpack_from("<IIII", data, offset + 8)
            strings = data[stroff:stroff + strsize]
            symbols = {}
            for index in range(nsyms):
                name, _, _, _, value = struct.unpack_from("<IBBHQ", data, symoff + index * 16)
                assert name < len(strings)
                symbol = strings[name:strings.index(b"\0", name)].decode()
                if value:
                    symbols[symbol] = value
            result["symbols"] = symbols
        offset += size
    assert {"uuid", "text_vmaddr", "text_fileoff", "symbols"} <= result.keys()
    return result


def call_site(members, binary_name, sample_name, disassembly_name, function, target):
    data = members[binary_name]
    identity = macho(data)
    sample = members[sample_name].decode()
    load = int(re.search(r"Load Address:\s+(0x[0-9a-f]+)", sample)[1], 16)
    assert f"<{identity['uuid']}>" in sample
    match = re.search(rf"{function}\s+\(in [^)]+\) \+ (\d+)\s+\[(0x[0-9a-f]+)\]", sample)
    offset, address = int(match[1]), int(match[2], 16)
    translated = address - load + identity["text_vmaddr"]
    assert translated == identity["symbols"]["_" + function] + offset
    lines = members[disassembly_name].decode().splitlines()
    line = next(index for index, text in enumerate(lines)
                if text.startswith(f"{translated:016x}\t"))
    previous = lines[line - 1]
    assert previous.startswith(f"{translated - 4:016x}\t")
    assert "\tbl\t" in previous and target in previous
    # Check the retained arm64 bytes contain a BL at the displayed call site.
    position = translated - 4 - identity["text_vmaddr"] + identity["text_fileoff"]
    instruction = struct.unpack_from("<I", data, position)[0]
    assert instruction & 0xFC000000 == 0x94000000
    immediate = instruction & 0x03FFFFFF
    if immediate & 0x02000000:
        immediate -= 0x04000000
    destination = translated - 4 + immediate * 4
    if target in identity["symbols"]:
        assert destination == identity["symbols"][target]
    return {"binary_uuid": identity["uuid"],
            "binary_sha256": hashlib.sha256(data).hexdigest(),
            "sample_function": function, "sample_function_offset": offset,
            "sample_runtime_return_pc": hex(address),
            "binary_return_pc": hex(translated),
            "call_destination": hex(destination),
            "preceding_call": previous,
            "disassembly_excerpt": lines[max(0, line - 10):line + 28]}


def main():
    provenance = json.loads((HERE / "historical-provenance.json").read_text())
    path = HERE / provenance["archive"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == provenance["archive_sha256"]
    members = read_archive(path)
    assert {name: hashlib.sha256(data).hexdigest() for name, data in members.items()} == provenance["members_sha256"]
    original = HERE / provenance["source_archive"]
    assert hashlib.sha256(original.read_bytes()).hexdigest() == provenance["source_archive_sha256"]
    archived = read_archive(original)
    for name in ("terminal-fault-orphan.json", "signal-edge-orphan.json",
                 "terminal-fault-orphan-stack.txt", "signal-edge-orphan-stack.txt",
                 "native-jobs.log", "native-full.log"):
        assert members[name] == archived["build/retention-diagnostics-validation/" + name]
    terminal_main = call_site(members, "execute_faults-original", "terminal-fault-orphan-stack.txt",
                              "execute-faults-disassembly.txt", "main", "_csh_execute_context_ast")
    terminal_child = call_site(members, "execute_faults-original", "terminal-fault-orphan-stack.txt",
                               "execute-faults-disassembly.txt", "context_job", "_sigprocmask")
    signal_child = call_site(members, "signal_edges_helper-original", "signal-edge-orphan-stack.txt",
                             "signal-helper-disassembly.txt", "main", "_raise")
    assert "launch signal %d returned %d" in "\n".join(terminal_main["disassembly_excerpt"])
    terminal = json.loads(members["terminal-fault-orphan.json"])
    signal = json.loads(members["signal-edge-orphan.json"])
    metadata = json.loads(members["metadata.json"])
    assert terminal["pid"] == 18538 and signal["pid"] == 99718
    snapshot = metadata["old_process_snapshot"]
    assert snapshot["returncode"] == 1 and snapshot["stdout"] == "" and snapshot["stderr"] == ""
    assert all(row["matches_original_base"] for row in metadata["source_files"].values())
    jobs_log = members["native-jobs.log"].decode()
    expected = ["PTY timeout after 5s waiting for process exit", "process snapshot exceeded cleanup deadline",
                "could not kill group 18494: [Errno 1] Operation not permitted", "0 captured bytes"]
    assert all(text in jobs_log for text in expected)
    result = {
        "original_source_base": provenance["original_base"],
        "original_artifact_bytes_preserved": True,
        "terminal": {"pid": terminal["pid"], "session": terminal["session"], "group": terminal["group"],
                     "retained_orphan_observation": terminal,
                     "main_call_site": terminal_main, "child_call_site": terminal_child,
                     "localized_subcase": "pending launch-signal loop: INT, TSTP, TERM, or QUIT",
                     "specific_signal": None,
                     "sample_scope": "post-failure orphan, not original timeout-time parent"},
        "signal_probe": {"pid": signal["pid"], "session": signal["session"], "group": signal["group"],
                         "retained_orphan_observation": signal, "child_call_site": signal_child,
                         "known_signal_from_command_and_failed_case": "SIGQUIT (3)",
                         "sample_scope": "post-failure orphan, not original timeout-time parent"},
        "current_observation_metadata": metadata,
        "limits": ["Stack/call-site localization does not establish the terminal loop's signal value.",
                   "Both historical PIDs were absent at review, without a host reboot since their launches.",
                   "Time and cause of their eventual disappearance are not recorded.",
                   "Leader-group EPERM does not describe a kill of the child's distinct group.",
                   "The shared cleanup snapshot deadline does not prove one slow ps invocation.",
                   "No root-cause attribution to crash notification follows from these historical files alone."]}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
