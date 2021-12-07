import os
from multiprocessing import Process
from pathlib import Path
from shutil import rmtree

import pytest
import rocksdb
from rocksdb.errors import RocksIOError
from time import sleep


class TestDBPath:
    leveldb = 'test_leveldb'
    rocksdb = 'test_rocksdb'


def print_process_info(title):
    print("\n--------------------------")
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())


def f_rocksdb(name: str):
    print_process_info(f'function f_rocksdb({name})')
    data = b'test_test_test'

    try:
        db = rocksdb.DB(TestDBPath.rocksdb, rocksdb.Options(create_if_missing=True))
        db.put(b'name', data)
    except RocksIOError:
        sleep(0.1)
        db = rocksdb.DB(TestDBPath.rocksdb, rocksdb.Options(create_if_missing=True), read_only=True)
        if data != db.get(b"name"):
            exit(-1)

    sleep(1)


def delete_test_db_dirs():
    db_paths = [Path(f"./{TestDBPath.leveldb}"), Path(f"./{TestDBPath.rocksdb}")]

    for db_path in db_paths:
        if db_path.exists():
            print(f'delete DB({db_path.resolve()})')
            rmtree(db_path)


@pytest.fixture(autouse=True)
def run_around_tests():
    delete_test_db_dirs()
    yield
    delete_test_db_dirs()


class TestMultiProcessLevelDB:
    def test_multiprocessing_rocksdb(self):
        p1 = Process(target=f_rocksdb, args=('rocksdb_prop1',))
        p1.start()

        p2 = Process(target=f_rocksdb, args=('rocksdb_prop2',))
        p2.start()

        p1.join()
        p2.join()

        # RocksDB supports multiprocessing.
        assert p1.exitcode == 0
        assert p2.exitcode == 0