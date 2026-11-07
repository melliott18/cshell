"""Bounded, compact large-file recipes and streaming byte-for-byte checks."""
import hashlib

MAX_FILE = 16 * 1024 * 1024


def chunks(recipe):
    parts = recipe if isinstance(recipe, list) else [recipe]
    total = 0
    for part in parts:
        pattern, count, suffix = part['pattern'], part['repeat'], part.get('suffix', b'')
        size = len(pattern) * count + len(suffix)
        total += size
        if not pattern or not isinstance(count, int) or count < 0 or total > MAX_FILE:
            raise ValueError('invalid or oversized text fixture recipe')
        step = max(1, 65536 // len(pattern))
        while count:
            take = min(step, count)
            yield pattern * take
            count -= take
        if suffix:
            yield suffix


def write_recipe(path, recipe):
    digest = hashlib.sha256()
    size = 0
    with path.open('wb') as stream:
        for chunk in chunks(recipe):
            stream.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    return dict(bytes=size, sha256=digest.hexdigest())


def check_recipe(path, recipe):
    """Compare every byte, including length; hashes are evidence, not the oracle."""
    expected_hash, actual_hash = hashlib.sha256(), hashlib.sha256()
    expected_size = actual_size = 0
    mismatch = None
    if not path.is_file():
        return dict(matches=False, error='missing output file')
    with path.open('rb') as stream:
        for expected in chunks(recipe):
            actual = stream.read(len(expected))
            expected_hash.update(expected)
            actual_hash.update(actual)
            if mismatch is None and actual != expected:
                mismatch = expected_size + next((i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]), len(actual))
            expected_size += len(expected)
            actual_size += len(actual)
        extra = stream.read(1)
        if extra and mismatch is None:
            mismatch = expected_size
        # A failed oversized file is recorded without reading unbounded bytes.
        if extra:
            actual_size = path.stat().st_size
    return dict(matches=mismatch is None, expected_bytes=expected_size, actual_bytes=actual_size,
                expected_sha256=expected_hash.hexdigest(),
                actual_sha256=actual_hash.hexdigest() if not extra else None,
                first_mismatch_offset=mismatch)
