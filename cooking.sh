#!/bin/bash
set -euo pipefail

usage() {
    echo "usage: cooking.sh [-p|--push] <commit-msg>"
    exit 1
}

PUSH=0

for arg in "$@"; do
    case "$arg" in
        -p|--push) PUSH=1 ;;
        *) ;;
    esac
done

# Update Merkle root hash + manifest
echo "==> Updating manifest..."
python3 secure_blog.py

# Build blog
echo "==> Building blog..."
python3 build.py

# If pushing option enabled, commit and push to production
if [[ $PUSH -eq 1 ]]; then
    echo "==> Committing and pushing..."
    git add -A
    git commit -m "$2"
    git push
fi

echo "Done."
