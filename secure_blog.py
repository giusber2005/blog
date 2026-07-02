#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

from verify import verify_proof

CONTENT_DIRS = ['content', 'articles', 'docs', 'static']
MANIFEST = 'manifest.json'


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_tree(leaves: list) -> list:
    """Returns list of layers (leaf→root). Each layer padded to even length."""
    layer = list(leaves)
    layers = []
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layers.append(layer[:])
        layer = [
            hashlib.sha256((layer[i] + layer[i + 1]).encode()).hexdigest()
            for i in range(0, len(layer), 2)
        ]
    layers.append(layer)
    return layers


def get_proof(layers: list, index: int) -> list:
    proof = []
    for layer in layers[:-1]:
        if index % 2 == 0:
            proof.append({"hash": layer[index + 1], "position": "right"})
        else:
            proof.append({"hash": layer[index - 1], "position": "left"})
        index //= 2
    return proof


def calculate():
    files = []
    for d in CONTENT_DIRS:
        p = Path(d)
        if p.exists():
            files.extend(sorted(f for f in p.rglob('*') if f.is_file() and f.suffix in {'.txt', '.tex', '.pdf'}))

    if not files:
        print("No files found.")
        return None

    file_hashes = [(str(f), hash_file(f)) for f in files]
    leaves = [h for _, h in file_hashes]
    layers = build_tree(leaves)
    root = layers[-1][0]

    manifest = {"root": root, "files": {}}
    for i, (path, fhash) in enumerate(file_hashes):
        manifest["files"][path] = {"hash": fhash, "proof": get_proof(layers, i)}

    Path(MANIFEST).write_text(json.dumps(manifest, indent=2))
    print(f"root:  {root}")
    print(f"wrote: {MANIFEST} ({len(files)} files)")
    return root


def main():
    if len(sys.argv) == 1:
        calculate()
    elif sys.argv[1] == 'verify' and len(sys.argv) == 3:
        target = sys.argv[2]
        try:
            ok = verify_proof(target, MANIFEST)
        except KeyError as e:
            print(e)
            sys.exit(1)
        print(f"{'OK' if ok else 'TAMPERED'}: {target}")
        sys.exit(0 if ok else 1)
    else:
        print("usage: secure_blog.py [verify <file>]")
        sys.exit(1)


if __name__ == "__main__":
    main()
