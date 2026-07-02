import hashlib

def verify_proof(file_bytes, proof, expected_root):
    current = hashlib.sha256(file_bytes).hexdigest()
    for step in proof:
        sibling = step["hash"]
        if step["position"] == "right":
            current = hashlib.sha256((current + sibling).encode()).hexdigest()
        else:
            current = hashlib.sha256((sibling + current).encode()).hexdigest()
    return current == expected_root
