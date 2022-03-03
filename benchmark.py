"""Benchmark each store type"""
import pytest
import time

from kona.key_value_store import KeyValueStoreError, KeyValueStore


class TestBenchmarkStoreTypes:
    store_types = ['dict', 'rocksdb', 'lmdb']

    def _new_store(self, uri, store_type=None, create_if_missing=True):
        try:
            if store_type == KeyValueStore.STORE_TYPE_DICT:
                from kona.key_value_store_dict import KeyValueStoreDict
                return KeyValueStoreDict()

            return KeyValueStore.new(uri, store_type=store_type, create_if_missing=create_if_missing)
        except KeyValueStoreError as e:
            print(f"Doesn't need to clean the store. uri={uri}, e={e}")

        return KeyValueStore.new(uri, store_type=store_type, create_if_missing=True)

    def _store_write_batch(self, store, data_prefix: str):
        batch = store.WriteBatch()

        data_prefix_1 = f'{data_prefix}_1'
        data_prefix_2 = f'{data_prefix}_2'

        batch.put(f'{data_prefix_1}_key'.encode(), f'{data_prefix_1}_value'.encode())
        batch.put(f'{data_prefix_2}_key'.encode(), f'{data_prefix_2}_value'.encode())

        with pytest.raises(KeyError):
            store.get(f'{data_prefix_1}_key'.encode())
        with pytest.raises(KeyError):
            store.get(f'{data_prefix_2}_key'.encode())

        batch.write()
        assert store.get(f'{data_prefix_1}_key'.encode()) == f'{data_prefix_1}_value'.encode()
        assert store.get(f'{data_prefix_2}_key'.encode()) == f'{data_prefix_2}_value'.encode()

    def _store_put_get(self, store, data_prefix: str):
        data_prefix_1 = f'{data_prefix}_1'
        data_prefix_2 = f'{data_prefix}_2'

        store.put(f'{data_prefix_1}_key'.encode(), f'{data_prefix_1}_value'.encode())
        store.put(f'{data_prefix_2}_key'.encode(), f'{data_prefix_2}_value'.encode())

        assert store.get(f'{data_prefix_1}_key'.encode()) == f'{data_prefix_1}_value'.encode()
        assert store.get(f'{data_prefix_2}_key'.encode()) == f'{data_prefix_2}_value'.encode()

    @pytest.mark.parametrize("store_type", store_types, ids=store_types)
    def test_benchmark_store_write_batch(self, store_type):
        start = time.perf_counter()
        store = self._new_store("file://./key_value_store_test_benchmark", store_type=store_type)

        repeat_times = 20000
        for i in range(repeat_times):
            self._store_write_batch(store, f'test_benchmark_{i}')

        store.destroy_store()
        print(f"Execution({repeat_times}) in {time.perf_counter() - start} seconds")

    @pytest.mark.parametrize("store_type", store_types, ids=store_types)
    def test_benchmark_store_put_get(self, store_type):
        start = time.perf_counter()
        store = self._new_store("file://./key_value_store_test_benchmark", store_type=store_type)

        repeat_times = 20000
        for i in range(repeat_times):
            self._store_put_get(store, f'test_benchmark_{i}')

        store.destroy_store()
        print(f"Execution({repeat_times}) in {time.perf_counter() - start} seconds")


def main():
    pytest.main(["benchmark.py", "-svx"])
