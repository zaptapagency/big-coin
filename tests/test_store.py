import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import node  # noqa: E402
import transaction  # noqa: E402
from block import genesis_block  # noqa: E402
from store import BlockStore, load_chain, save_chain  # noqa: E402


def _mine_chain(num_blocks: int):
    """Build a Node with maturity=0 and mine `num_blocks` blocks onto it."""
    n = node.Node("miner", coinbase_maturity=0)
    _, pub = transaction.generate_keypair()
    pkh = transaction.pubkey_hash(pub)
    for _ in range(num_blocks):
        block = n.mine_block(pkh)
        assert block is not None
    return n


def test_save_and_reload_matches_state(tmp_path):
    n = _mine_chain(4)
    chain = n.chain

    db = str(tmp_path / "blocks.db")
    with BlockStore(db) as store:
        saved = save_chain(chain, store)
        assert saved == len(chain.blocks)
        rebuilt = load_chain(store, coinbase_maturity=0)

    assert rebuilt.tip == chain.tip
    assert rebuilt.height == chain.height
    assert len(rebuilt.utxo) == len(chain.utxo)
    assert rebuilt.utxo.total_value() == chain.utxo.total_value()


def test_has_and_get_block_roundtrip(tmp_path):
    n = _mine_chain(3)
    chain = n.chain

    db = str(tmp_path / "blocks.db")
    with BlockStore(db) as store:
        save_chain(chain, store)
        for block_hash, block in chain.blocks.items():
            assert store.has_block(block_hash)
            fetched = store.get_block(block_hash)
            assert fetched is not None
            assert fetched.hash == block_hash
            assert fetched.to_dict() == block.to_dict()

        assert not store.has_block("f" * 64)
        assert store.get_block("f" * 64) is None


def test_load_blocks_in_height_order(tmp_path):
    n = _mine_chain(4)
    chain = n.chain

    db = str(tmp_path / "blocks.db")
    with BlockStore(db) as store:
        save_chain(chain, store)
        blocks = store.load_blocks_in_height_order()

    heights = [chain.heights[b.hash] for b in blocks]
    assert heights == sorted(heights)  # non-decreasing
    assert blocks[0].hash == genesis_block().hash  # genesis first


def test_persistence_across_restart(tmp_path):
    n = _mine_chain(4)
    chain = n.chain

    db = str(tmp_path / "blocks.db")
    store = BlockStore(db)
    save_chain(chain, store)
    store.close()

    # Reopen a brand-new store on the same DB file (simulated restart).
    store2 = BlockStore(db)
    rebuilt = load_chain(store2, coinbase_maturity=0)
    store2.close()

    assert rebuilt.tip == chain.tip
    assert rebuilt.height == chain.height


def test_count_equals_number_of_blocks(tmp_path):
    n = _mine_chain(4)
    chain = n.chain

    db = str(tmp_path / "blocks.db")
    with BlockStore(db) as store:
        save_chain(chain, store)
        assert store.count() == len(chain.blocks)
