import functools
import gc
import rocksdb
import urllib.parse
from pathlib import Path

from kona.key_value_store import KeyValueStoreError
from kona.key_value_store import KeyValueStoreWriteBatch, KeyValueStoreCancelableWriteBatch, KeyValueStore
from kona.key_value_store import _validate_args_bytes, _validate_args_bytes_without_first

rocksdb_exceptions = [rocksdb.errors.NotFound,
                      rocksdb.errors.Corruption,
                      rocksdb.errors.NotSupported,
                      rocksdb.errors.InvalidArgument,
                      rocksdb.errors.RocksIOError,
                      rocksdb.errors.MergeInProgress,
                      rocksdb.errors.Incomplete]


def _error_convert(func):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if type(e) in rocksdb_exceptions:
                raise KeyValueStoreError(e)
            raise e

    return _wrapper


class _KeyValueStoreWriteBatchRocksDB(KeyValueStoreWriteBatch):
    def __init__(self, db: rocksdb.DB, sync: bool):
        self._db = db
        self._sync = sync
        self._batch = self._new_batch()

    @_error_convert
    def _new_batch(self):
        return rocksdb.WriteBatch()

    @_validate_args_bytes_without_first
    @_error_convert
    def put(self, key: bytes, value: bytes):
        self._batch.put(key, value)

    @_validate_args_bytes_without_first
    @_error_convert
    def delete(self, key: bytes):
        self._batch.delete(key)

    @_error_convert
    def clear(self):
        self._batch.clear()

    @_error_convert
    def write(self):
        self._db.write(self._batch, sync=self._sync)


class _KeyValueStoreCancelableWriteBatchRocksDB(KeyValueStoreCancelableWriteBatch):
    def __init__(self, store: KeyValueStore, db: rocksdb.DB, sync: bool):
        super().__init__(store, sync=sync)
        self._touched_keys = set()
        self._db = db
        self._snapshot = db.snapshot()

    def _touch(self, key: bytes):
        self._touched_keys.add(key)

    def _get_original_touched_item(self):
        for key in self._touched_keys:
            try:
                yield key, self._db.get(key, snapshot=self._snapshot)
            except KeyError:
                return key, None

    def clear(self):
        super().clear()
        self._touched_keys.clear()

    def close(self):
        self._snapshot.close()
        self._snapshot = None


class KeyValueStoreRocksDB(KeyValueStore):
    def __init__(self, uri: str, **kwargs):
        uri_obj = urllib.parse.urlparse(uri)
        if uri_obj.scheme != 'file':
            raise ValueError(f"Support file path URI only (ex. file:///xxx/xxx). uri={uri}")
        self._path = f"{(uri_obj.netloc if uri_obj.netloc else '')}{uri_obj.path}"
        self._db = self._new_db(self._path, **kwargs)

    @_error_convert
    def _new_db(self, path, **kwargs) -> rocksdb.DB:
        return rocksdb.DB(path, rocksdb.Options(**kwargs))

    @_validate_args_bytes_without_first
    @_error_convert
    def get(self, key: bytes, *, default=None, **kwargs) -> bytes:
        if default is not None:
            _validate_args_bytes(default)

        result = self._db.get(key, **kwargs) or default
        if result is None:
            raise KeyError(f"Has no value of key({key})")
        return result

    @_validate_args_bytes_without_first
    @_error_convert
    def put(self, key: bytes, value: bytes, *, sync=False, **kwargs):
        self._db.put(key, value, sync=sync, **kwargs)

    @_validate_args_bytes_without_first
    @_error_convert
    def delete(self, key: bytes, *, sync=False, **kwargs):
        self._db.delete(key, sync=sync, **kwargs)

    @_error_convert
    def close(self):
        if self._db:
            del self._db
            gc.collect()
            self._db = None

    @_error_convert
    def destroy_store(self):
        self.close()

        def rm_tree(path: Path):
            for child in path.iterdir():
                if child.is_file():
                    child.unlink()
                else:
                    rm_tree(child)
            path.rmdir()

        rm_tree(Path(self._path))

    @_error_convert
    def WriteBatch(self, sync=False) -> KeyValueStoreWriteBatch:
        return _KeyValueStoreWriteBatchRocksDB(self._db, sync=sync)

    @_error_convert
    def CancelableWriteBatch(self, sync=False) -> KeyValueStoreCancelableWriteBatch:
        return _KeyValueStoreCancelableWriteBatchRocksDB(self, self._db, sync=sync)

    @_error_convert
    def Iterator(self, start_key: bytes = None, stop_key: bytes = None, include_value: bool = True, **kwargs):
        """Get Iterator

        :param start_key:
        :param stop_key:
        :param include_value:  # This parameter is not handled in rocksdb.
        :param kwargs:  # This parameter is not handled in rocksdb.
        :return:
        """
        if 'start' in kwargs or 'stop' in kwargs:
            raise ValueError("Use start_key and stop_key arguments instead of start and stop arguments")

        it = self._db.iteritems()
        try:
            it.seek(start_key)
        except TypeError:
            it.seek_to_first()

        for key, value in it:
            yield key, value
            if stop_key and stop_key == key:
                return
