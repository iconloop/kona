"""Test KeyValueStore class"""
import pytest

from kona.key_value_store import KeyValueStoreError, KeyValueStore


class TestKeyValueStore:
    store_types = ['dict', 'rocksdb']

    def _get_test_items(self, count: int = 5):
        test_items = dict()
        for i in range(1, count + 1):
            key = bytes(f"test_key_{i}", encoding='utf-8')
            value = bytes(f"test_value_{i}", encoding='utf-8')
            test_items[key] = value
        return test_items

    def _new_store(self, uri, store_type=None, create_if_missing=True):
        try:
            if store_type == KeyValueStore.STORE_TYPE_DICT:
                from kona.key_value_store_dict import KeyValueStoreDict
                print(f"New KeyValueStore. store_type={store_type}, uri={uri}")
                return KeyValueStoreDict()

            return KeyValueStore.new(uri, store_type=store_type, create_if_missing=create_if_missing)
        except KeyValueStoreError as e:
            print(f"Doesn't need to clean the store. uri={uri}, e={e}")

        return KeyValueStore.new(uri, store_type=store_type, create_if_missing=True)

    @pytest.mark.parametrize("store_type", store_types, ids=store_types)
    def test_key_value_store_basic(self, store_type):
        test_items = self._get_test_items(5)
        print(f"test_items={test_items}")

        store = self._new_store("file://./key_value_store_test_basic", store_type=store_type)

        #
        # put/get
        #

        for key, value in test_items.items():
            store.put(key, value)
            assert store.get(key) == value

        with pytest.raises(KeyError):
            store.get(b'unknown_key')

        assert store.get(b'unknown_key', default=b'test_default_value') == b'test_default_value'

        kwargs = {}

        if store_type == 'dict':
            container = tuple(test_items.keys())
        else:
            kwargs.update({
                'start_key': b'test_key_2',
                'stop_key': b'test_key_4'
            })
            container = (b'test_key_2', b'test_key_3', b'test_key_4')
        expect_count = len(container)

        count = 0
        for key, value in store.Iterator(**kwargs):
            assert key in container
            count += 1
        assert count == expect_count

        count = 0
        for key, value in store.Iterator(**kwargs):
            assert key in container
            count += 1
        assert count == expect_count

        count = 0
        for key, value in store.Iterator(**kwargs):
            assert key in container
            count += 1
        assert count == expect_count

        #
        # delete
        #

        del_key = b'test_key_2'
        del test_items[del_key]
        store.delete(del_key)
        with pytest.raises(KeyError):
            store.get(del_key)

        count = 0
        for key, value in store.Iterator():
            print(f"DB iterator: key={key}, value={value}")
            assert value == test_items[bytes(key)]
            count += 1
        print(f"Count after {del_key} has been deleted={count}")
        assert count == len(test_items)

        store.destroy_store()

    @pytest.mark.parametrize("store_type", store_types, ids=store_types)
    def test_key_value_store_write_batch(self, store_type):
        store = self._new_store("file://./key_value_store_test_write_batch", store_type=store_type)

        batch = store.WriteBatch()
        batch.put(b'test_key_1', b'test_value_1')
        batch.put(b'test_key_2', b'test_value_2')

        with pytest.raises(KeyError):
            store.get(b'test_key_1')
        with pytest.raises(KeyError):
            store.get(b'test_key_2')

        batch.write()
        assert store.get(b'test_key_1') == b'test_value_1'
        assert store.get(b'test_key_2') == b'test_value_2'

        store.destroy_store()

    @pytest.mark.parametrize("store_type", store_types, ids=store_types)
    def test_key_value_store_cancelable_write_batch(self, store_type):
        test_items = self._get_test_items(5)

        store = self._new_store("file://./key_value_store_test_cancelable_write_batch", store_type=store_type)

        for key, value in test_items.items():
            store.put(key, value)

        cancelable_batch = store.CancelableWriteBatch()
        cancelable_batch.put(b'cancelable_key_1', b'cancelable_value_1')
        cancelable_batch.put(b'test_key_2', b'edited_test_value_2')
        cancelable_batch.put(b'cancelable_key_2', b'cancelable_value_2')
        cancelable_batch.put(b'test_key_4', b'edited_test_value_4')
        cancelable_batch.write()

        edited_test_items = test_items.copy()
        edited_test_items[b'cancelable_key_1'] = b'cancelable_value_1'
        edited_test_items[b'test_key_2'] = b'edited_test_value_2'
        edited_test_items[b'cancelable_key_2'] = b'cancelable_value_2'
        edited_test_items[b'test_key_4'] = b'edited_test_value_4'

        count = 0
        print("before cancel")
        for key, value in store.Iterator():
            print(f"Edited DB iterator: key={key}, value={value}")
            assert value == edited_test_items[bytes(key)]
            count += 1
        print(f"Count after cancelable_batch has been written={count}")

        assert count == len(edited_test_items)

        cancelable_batch.cancel()
        count = 0
        print("after cancel")
        for key, value in store.Iterator():
            print(f"Original DB iterator: key={key}, value={value}")
            assert value == test_items[bytes(key)]
            count += 1
        print(f"Original count={count}")
        assert count == len(test_items)

        store.destroy_store()
