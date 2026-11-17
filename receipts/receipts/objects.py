"""Content-addressed storage for file versions referenced by receipts."""
import hashlib
import os
import re

from .models import sha256_bytes

HEX_SHA = re.compile(r"^[0-9a-f]{64}$")
CHUNK = 1024 * 1024


class ObjectStore:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)
        os.chmod(self.root, 0o700)

    def path_for(self, sha):
        if not isinstance(sha, str) or not HEX_SHA.match(sha):
            raise ValueError("invalid object sha: %r" % (sha,))
        return os.path.join(self.root, sha[:2], sha)

    def put_bytes(self, data):
        sha = sha256_bytes(data)
        path = self.path_for(sha)
        if not os.path.exists(path):
            parent = os.path.dirname(path)
            os.makedirs(parent, exist_ok=True)
            os.chmod(parent, 0o700)
            tmp = path + ".tmp-%d" % os.getpid()
            with open(tmp, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
        return sha

    def put_file(self, path):
        digest = hashlib.sha256()
        chunks = []
        with open(path, "rb") as f:
            while True:
                block = f.read(CHUNK)
                if not block:
                    break
                digest.update(block)
                chunks.append(block)
        data = b"".join(chunks)
        if sha256_bytes(data) != digest.hexdigest():
            raise IOError("file changed while hashing: %s" % path)
        return self.put_bytes(data)

    def get(self, sha):
        path = self.path_for(sha)
        if not os.path.isfile(path):
            raise FileNotFoundError("missing object %s" % sha)
        with open(path, "rb") as f:
            data = f.read()
        if sha256_bytes(data) != sha:
            raise ValueError("object content hash mismatch: %s" % sha)
        return data

    def has(self, sha):
        return os.path.isfile(self.path_for(sha))

    def verify_all(self):
        corrupt = []
        if not os.path.isdir(self.root):
            return corrupt
        for prefix in sorted(os.listdir(self.root)):
            directory = os.path.join(self.root, prefix)
            if not os.path.isdir(directory):
                continue
            for name in sorted(os.listdir(directory)):
                if not HEX_SHA.match(name):
                    continue
                path = os.path.join(directory, name)
                with open(path, "rb") as f:
                    if sha256_bytes(f.read()) != name:
                        corrupt.append(name)
        return corrupt
