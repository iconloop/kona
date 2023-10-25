"""Test KeyValueStoreLMDB"""
from kona.key_value_store import KeyValueStore


class TestKeyValueStoreLMDB:
    def test_lmdb_options(self):
        lmdb_store = KeyValueStore.new(
            "file://./key_value_store_test_lmdb",
            store_type="lmdb",
            invalid_kwarg="I'm not part of lmdb",
            map_size=12345,
            max_readers=999,
        )

        assert 12345 == lmdb_store._db.info()["map_size"]
        assert 999 == lmdb_store._db.info()["max_readers"]

        lmdb_store.destroy_store()
