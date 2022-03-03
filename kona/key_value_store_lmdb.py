import functools
import urllib.parse
from pathlib import Path
from typing import Tuple, Any

import gc
import lmdb

from kona.key_value_store import KeyValueStoreError
from kona.key_value_store import KeyValueStoreWriteBatch, KeyValueStoreCancelableWriteBatch, KeyValueStore
from kona.key_value_store import _validate_args_bytes, _validate_args_bytes_without_first

lmdb_exceptions = [lmdb.Error,
                   lmdb.KeyExistsError,
                   lmdb.NotFoundError,
                   lmdb.PageNotFoundError,
                   lmdb.CorruptedError,
                   lmdb.PanicError,
                   lmdb.VersionMismatchError,
                   lmdb.InvalidError,
                   lmdb.MapFullError,
                   lmdb.DbsFullError,
                   lmdb.ReadersFullError,
                   lmdb.TlsFullError,
                   lmdb.TxnFullError,
                   lmdb.CursorFullError,
                   lmdb.PageFullError,
                   lmdb.MapResizedError,
                   lmdb.IncompatibleError,
                   lmdb.BadDbiError,
                   lmdb.BadRslotError,
                   lmdb.BadTxnError,
                   lmdb.BadValsizeError,
                   lmdb.ReadonlyError,
                   lmdb.InvalidParameterError,
                   lmdb.LockError,
                   lmdb.MemoryError,
                   lmdb.DiskError]


def _error_convert(func):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if type(e) in lmdb_exceptions:
                raise KeyValueStoreError(e)
            raise e

    return _wrapper


class _KeyValueStoreWriteBatchLMDB(KeyValueStoreWriteBatch):
    def __init__(self, db: lmdb.Environment):
        self._db = db
        self._txn = self._new_txn()

    @_error_convert
    def _new_txn(self):
        return self._db.begin(write=True)

    @_validate_args_bytes_without_first
    @_error_convert
    def put(self, key: bytes, value: bytes):
        self._txn.put(key, value)

    @_validate_args_bytes_without_first
    @_error_convert
    def delete(self, key: bytes):
        self._txn.delete(key)

    @_error_convert
    def clear(self):
        self._txn.abort()

    @_error_convert
    def write(self):
        self._txn.commit()


class _KeyValueStoreCancelableWriteBatchLMDB(KeyValueStoreCancelableWriteBatch):
    def __init__(self, store: KeyValueStore, db: lmdb.Environment):
        super().__init__(store)
        self._original_items = dict()
        self._db = db

    def _touch(self, key: bytes):
        if key in self._original_items:
            return

        value = self._db.begin().get(key, None)
        self._original_items[key] = value

    def _get_original_touched_item(self):
        for key, value in self._original_items.items():
            yield key, value

    def clear(self):
        super().clear()
        self._original_items.clear()

    def close(self):
        self._original_items: dict = None


class KeyValueStoreLMDB(KeyValueStore):
    def __init__(self, uri: str, **kwargs):
        uri_obj = urllib.parse.urlparse(uri)
        if uri_obj.scheme != 'file':
            raise ValueError(f"Support file path URI only (ex. file:///xxx/xxx). uri={uri}")
        self._path = f"{(uri_obj.netloc if uri_obj.netloc else '')}{uri_obj.path}"
        self._db = self._new_db(self._path)

    @_error_convert
    def _new_db(self, path) -> lmdb.Environment:
        return lmdb.Environment(path)

    @_validate_args_bytes_without_first
    @_error_convert
    def get(self, key: bytes, *, default=None, **kwargs) -> bytes:
        if default is not None:
            _validate_args_bytes(default)

        with self._db.begin() as txn:
            result = txn.get(key, default)
            if result is None:
                raise KeyError(f"Has no value of key({key})")
            return result

    @_validate_args_bytes_without_first
    @_error_convert
    def put(self, key: bytes, value: bytes, *, sync=False, **kwargs):
        with self._db.begin(write=True) as txn:
            txn.put(key, value)

    @_validate_args_bytes_without_first
    @_error_convert
    def delete(self, key: bytes, *, sync=False, **kwargs):
        with self._db.begin(write=True) as txn:
            txn.delete(key)

    @_error_convert
    def close(self):
        if self._db:
            self._db.close()
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

    @_validate_args_bytes_without_first
    @_error_convert
    def key_may_exist(self, key: bytes) -> Tuple[bool, Any]:
        pass

    @_error_convert
    def WriteBatch(self, sync=False) -> KeyValueStoreWriteBatch:
        return _KeyValueStoreWriteBatchLMDB(self._db)

    @_error_convert
    def CancelableWriteBatch(self, sync=False) -> KeyValueStoreCancelableWriteBatch:
        return _KeyValueStoreCancelableWriteBatchLMDB(self, self._db)

    @_error_convert
    def Iterator(self, start_key: bytes = None, stop_key: bytes = None, include_value: bool = True, **kwargs):
        """Get Iterator

        :param start_key:
        :param stop_key:
        :param include_value:  # This parameter is not handled in lmdb
        :param kwargs:  # This parameter is not handled in lmdb
        :return:
        """
        if 'start' in kwargs or 'stop' in kwargs:
            raise ValueError("Use start_key and stop_key arguments instead of start and stop arguments")

        with self._db.begin() as txn:
            with txn.cursor() as cursor:
                cursor.set_range(start_key or b'')

                for key, value in cursor:
                    yield key, value
                    if stop_key and stop_key == key:
                        return
