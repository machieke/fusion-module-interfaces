"""Narrow host recipe selection; implementation remains the original recipe.

No native owner, runtime, image start, scheduler or cluster discovery lives
here. Optional chain key setup checks its cryptographic dependencies before
the original recipe creates any output or invokes OpenSSL/kubectl.
"""
import argparse
import sys

from fusion.contracts import require


def create_secrets():
    # Only select the supported package closure. The existing recipe owns full
    # CLI validation and all Secret creation. Never duplicate key/TLS logic.
    if not any(value in ('-h', '--help') for value in sys.argv[1:]):
        # Match argparse's existing abbreviation behavior, so --cha cannot
        # bypass the supported dependency-closure check.
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('--chain', action='store_true')
        parser.add_argument('--preview-values')
        selected, _ = parser.parse_known_args()
        chain = selected.chain
        if selected.preview_values:
            from integration.single_node.preview_secrets import selection
            profile, _ = selection(selected.preview_values)
            chain = chain or profile.get('chain', {}).get('enabled')
        if chain:
            try:
                from cryptography.hazmat.primitives.asymmetric import ec
                from Crypto.Hash import keccak
            except (ImportError, OSError):
                require(False, 'NOT_AVAILABLE')
    from fusion_operator.recipes.create_secrets import main
    main()
