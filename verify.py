import hashlib
import json
import sys
from pathlib import Path


def verify_proof(file_path, manifest):
    """Verify file_path against manifest (dict or path to manifest.json)."""
    if isinstance(manifest, (str, Path)):
        manifest = json.loads(Path(manifest).read_text())

    key = str(file_path)
    if key not in manifest['files']:
        raise KeyError(f"not in manifest: {key}")

    entry = manifest['files'][key]
    current = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
    for step in entry['proof']:
        sibling = step['hash']
        if step['position'] == 'right':
            current = hashlib.sha256((current + sibling).encode()).hexdigest()
        else:
            current = hashlib.sha256((sibling + current).encode()).hexdigest()
    return current == manifest['root']


if __name__ == '__main__':
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print('usage: verify.py <file> [manifest.json]')
        sys.exit(1)
    manifest_path = sys.argv[2] if len(sys.argv) == 3 else 'manifest.json'
    ok = verify_proof(sys.argv[1], manifest_path)
    print(f"{'OK' if ok else 'TAMPERED'}: {sys.argv[1]}")
    sys.exit(0 if ok else 1)
