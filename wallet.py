"""MyCoin — Milestone 8: Wallet & Privacy (Bitcoin whitepaper section 10).

This module gives users a way to hold keys, derive human-shareable addresses,
check balances against a UTXO set, and build spendable transactions.

Privacy (whitepaper section 10): "a new key pair should be used for each
transaction to keep them from being linked to a common owner." `Wallet`
follows this: every send draws change to a freshly generated key, and callers
are encouraged to call `new_key()` per incoming payment.

Trade-offs vs. real Bitcoin (the "~10% difference"):
  * Addresses are Base58Check over a *single* SHA-256 public-key hash. Real
    Bitcoin uses RIPEMD-160(SHA-256(pubkey)) (a 20-byte HASH160). We avoid
    RIPEMD-160 because it is missing from some OpenSSL 3 builds; the Base58Check
    envelope (version byte + 4-byte double-SHA-256 checksum) is otherwise the
    same idea as a Bitcoin P2PKH address.
  * Keys here are generated at random on each `new_key()` call and kept in
    memory. Real wallets use hierarchical-deterministic derivation (BIP32/39)
    so all keys stem from one recoverable seed. Here there is no seed and no
    persistence — losing the process loses the keys.
  * Coin selection is a simple greedy "largest/first-fit" scan, not the more
    sophisticated selection real wallets use to minimize fees and change.
"""

from __future__ import annotations

from typing import Iterable

from transaction import (
    Transaction,
    TxInput,
    TxOutput,
    generate_keypair,
    pubkey_hash,
    sha256d,
)
from ecdsa import SigningKey, SECP256k1


# --------------------------------------------------------------------------- #
# Base58Check address encoding
# --------------------------------------------------------------------------- #
_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE = len(_ALPHABET)
_INDEX = {c: i for i, c in enumerate(_ALPHABET)}


def base58_encode(data: bytes) -> str:
    """Encode bytes to a Base58 string (Bitcoin alphabet).

    Leading zero bytes are preserved as leading '1' characters, matching
    Bitcoin's convention so that the version byte round-trips exactly.
    """
    # Count and strip leading zero bytes; they map to leading '1's.
    n_leading_zeros = 0
    for b in data:
        if b == 0:
            n_leading_zeros += 1
        else:
            break

    num = int.from_bytes(data, "big")
    chars: list[str] = []
    while num > 0:
        num, rem = divmod(num, _BASE)
        chars.append(_ALPHABET[rem])
    chars.append(_ALPHABET[0] * n_leading_zeros)
    return "".join(reversed(chars))


def base58_decode(s: str) -> bytes:
    """Decode a Base58 string back to bytes. Inverse of `base58_encode`."""
    # Leading '1's decode back to leading zero bytes.
    n_leading_ones = 0
    for c in s:
        if c == _ALPHABET[0]:
            n_leading_ones += 1
        else:
            break

    num = 0
    for c in s:
        if c not in _INDEX:
            raise ValueError(f"invalid base58 character: {c!r}")
        num = num * _BASE + _INDEX[c]

    # Convert the big integer back to bytes (minimal length), then re-prepend
    # the leading zero bytes that the '1' prefix represented.
    body = num.to_bytes((num.bit_length() + 7) // 8, "big") if num > 0 else b""
    return b"\x00" * n_leading_ones + body


def address_from_pubkey_hash(pkh_hex: str, version: int = 0x00) -> str:
    """Build a Base58Check address from a public-key hash (hex).

    payload   = version_byte || pubkey_hash_bytes
    checksum  = first 4 bytes of sha256d(payload)
    address   = base58_encode(payload || checksum)
    """
    payload = bytes([version]) + bytes.fromhex(pkh_hex)
    checksum = sha256d(payload)[:4]
    return base58_encode(payload + checksum)


def pubkey_hash_from_address(addr: str) -> str:
    """Decode an address back to its public-key hash (hex), verifying checksum.

    Raises ValueError if the address is malformed or the checksum is wrong.
    """
    raw = base58_decode(addr)
    if len(raw) < 5:  # need at least version(1) + checksum(4)
        raise ValueError("address too short")

    payload, checksum = raw[:-4], raw[-4:]
    if sha256d(payload)[:4] != checksum:
        raise ValueError("bad address checksum")

    # Drop the leading version byte; the rest is the pubkey hash.
    return payload[1:].hex()


def is_valid_address(addr: str) -> bool:
    """True if `addr` is a well-formed Base58Check address with a valid checksum."""
    try:
        pubkey_hash_from_address(addr)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Wallet
# --------------------------------------------------------------------------- #
class Wallet:
    """An in-memory keychain implementing "a new key pair per transaction".

    Keys are indexed by their pubkey_hash so that, given a UTXO locked to a
    hash, the wallet can find the signing key that authorizes spending it.
    """

    def __init__(self) -> None:
        # pubkey_hash (hex) -> SigningKey
        self._keys: dict[str, SigningKey] = {}
        # pubkey_hash (hex) -> address (base58), preserving insertion order
        self._addresses: dict[str, str] = {}
        # Minimal record of sends this wallet created.
        self.history: list[dict] = []

    # ----- key management ------------------------------------------------- #
    def new_key(self) -> str:
        """Generate a fresh keypair, store it, and return its Base58 address."""
        sk, pubkey_hex = generate_keypair()
        pkh = pubkey_hash(pubkey_hex)
        addr = address_from_pubkey_hash(pkh)
        self._keys[pkh] = sk
        self._addresses[pkh] = addr
        return addr

    @property
    def addresses(self) -> list[str]:
        """All addresses this wallet owns, in the order they were created."""
        return list(self._addresses.values())

    def owns(self, pubkey_hash_hex: str) -> bool:
        """True if this wallet holds the signing key for `pubkey_hash_hex`."""
        return pubkey_hash_hex in self._keys

    # ----- persistence ---------------------------------------------------- #
    def export_privkeys(self) -> list[str]:
        """Serialize every signing key as hex, for saving to disk."""
        return [sk.to_string().hex() for sk in self._keys.values()]

    def load_privkey(self, privkey_hex: str) -> str:
        """Restore a signing key from hex, re-deriving its address (returned).

        The pubkey_hash and Base58 address are deterministic functions of the
        key, so a reloaded key reproduces exactly the same address it had
        before, letting a wallet recover ownership of its coins after a restart.
        """
        sk = SigningKey.from_string(bytes.fromhex(privkey_hex), curve=SECP256k1)
        pubkey_hex = sk.get_verifying_key().to_string().hex()
        pkh = pubkey_hash(pubkey_hex)
        addr = address_from_pubkey_hash(pkh)
        self._keys[pkh] = sk
        self._addresses[pkh] = addr
        return addr

    # ----- balance -------------------------------------------------------- #
    def balance(self, utxos: Iterable[tuple[str, int, TxOutput]]) -> int:
        """Sum the amounts of UTXOs locked to a pubkey_hash this wallet owns."""
        return sum(
            out.amount for _txid, _idx, out in utxos if self.owns(out.pubkey_hash)
        )

    # ----- spending ------------------------------------------------------- #
    def create_transaction(
        self,
        utxos: Iterable[tuple[str, int, TxOutput]],
        to_address: str,
        amount: int,
        fee: int = 0,
        change_address: str | None = None,
    ) -> Transaction:
        """Build and sign a transaction paying `amount` to `to_address`.

        Only owned UTXOs are considered. Owned UTXOs are greedily accumulated
        until they cover `amount + fee`; otherwise ValueError("insufficient
        funds") is raised. Output 0 pays the recipient; any surplus over
        `amount + fee` is returned as change to `change_address` (default: a
        freshly generated address, honoring the "new key per transaction"
        privacy guidance). A zero-value change output is never created.
        """
        if amount <= 0:
            raise ValueError("amount must be positive")
        if fee < 0:
            raise ValueError("fee must be non-negative")

        target = amount + fee

        # Greedily select owned UTXOs until we cover the target.
        selected: list[tuple[str, int, TxOutput]] = []
        total = 0
        for txid, index, out in utxos:
            if not self.owns(out.pubkey_hash):
                continue
            selected.append((txid, index, out))
            total += out.amount
            if total >= target:
                break

        if total < target:
            raise ValueError("insufficient funds")

        # Build outputs: recipient first, then change (if any).
        outputs = [TxOutput(amount, pubkey_hash_from_address(to_address))]
        change = total - target
        if change > 0:
            if change_address is None:
                change_address = self.new_key()  # new key per transaction
            outputs.append(
                TxOutput(change, pubkey_hash_from_address(change_address))
            )

        # Build inputs referencing each selected UTXO.
        inputs = [
            TxInput(prev_txid=txid, output_index=index)
            for txid, index, _out in selected
        ]
        tx = Transaction(inputs=inputs, outputs=outputs)

        # Sign each input with the key for the UTXO it spends.
        for i, (_txid, _index, out) in enumerate(selected):
            tx.sign_input(i, self._keys[out.pubkey_hash])

        self.history.append({"txid": tx.txid, "amount": amount, "to": to_address})
        return tx
