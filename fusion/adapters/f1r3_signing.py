"""Pinned DeployDataProto signer reused by the local M4 composition.

Same BLAKE2b-256 / secp256k1 / low-S DER algorithm as chain_demo.py. Optional
dependencies are installed only by the chain recipe, never required by DA.
"""
import hashlib
from pathlib import Path

from ..contracts import require


def signer(secret_file, public, Proto):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    key = ec.derive_private_key(int(Path(secret_file).read_text().strip(), 16), ec.SECP256K1())
    actual = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex()
    require(actual == public, "CONFLICT")

    def sign(data):
        proto = Proto(**{k: v for k, v in data.items() if k != "expiration_timestamp"})
        hashed = hashlib.blake2b(proto.SerializeToString(), digest_size=32).digest()
        signature = key.sign(hashed, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        r, s = utils.decode_dss_signature(signature)
        order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        return {"data": data, "deployer": public, "sigAlgorithm": "secp256k1",
                "signature": utils.encode_dss_signature(r, min(s, order - s)).hex()}
    return sign
