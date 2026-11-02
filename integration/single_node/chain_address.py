"""Pure address encoding used by isolated synthetic chain key provisioning."""
import hashlib


def address(public):
    from Crypto.Hash import keccak
    def keccak256(data):
        return keccak.new(digest_bits=256, data=data).digest()
    payload = bytes(4) + keccak256(keccak256(public[1:])[-20:])
    raw = payload + hashlib.blake2b(payload, digest_size=32).digest()[:4]
    n, encoded = int.from_bytes(raw, "big"), ""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    while n:
        n, remainder = divmod(n, 58)
        encoded = alphabet[remainder] + encoded
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + encoded

