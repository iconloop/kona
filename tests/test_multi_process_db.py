import os
from multiprocessing import Process
from pathlib import Path
from shutil import rmtree
from time import sleep

import lmdb
import pytest
import rocksdb
from rocksdb.errors import RocksIOError


class TestDBPath:
    rocksdb = "test_rocksdb"
    lmdb = "test_lmdb"


def print_process_info(title):
    print("\n--------------------------")
    print(title)
    print("module name:", __name__)
    print("parent process:", os.getppid())
    print("process id:", os.getpid())


def f_rocksdb(name: str):
    print_process_info(f"function f_rocksdb({name})")
    data = b"test_test_test_rocksdb"

    try:
        db = rocksdb.DB(TestDBPath.rocksdb, rocksdb.Options(create_if_missing=True))
        db.put(b"name", data)
        print("f_rocksdb as a Writer")
    except RocksIOError:
        sleep(0.1)
        db = rocksdb.DB(TestDBPath.rocksdb, rocksdb.Options(create_if_missing=True), read_only=True)
        if data != db.get(b"name"):
            exit(-1)
        print("f_rocksdb as a Reader")
    sleep(1)


def f_lmdb(name: str):
    print_process_info(f"function f_lmdb({name})")
    data = b"test_test_test_lmdb"

    if name == "prop1":
        env = lmdb.open(TestDBPath.lmdb)
        with env.begin(write=True) as txn:
            txn.put(b"name", data)
        print("f_lmdb as a Writer")
    else:
        sleep(0.1)
        env = lmdb.open(TestDBPath.lmdb)
        with env.begin() as txn:
            if data != txn.get(b"name"):
                exit(-1)
        print("f_lmdb as a Reader")
    sleep(1)


def delete_test_db_dirs():
    db_paths = [Path(f"./{TestDBPath.lmdb}"), Path(f"./{TestDBPath.rocksdb}")]

    for db_path in db_paths:
        if db_path.exists():
            print(f"delete DB({db_path.resolve()})")
            rmtree(db_path)


@pytest.fixture(autouse=True)
def run_around_tests():
    delete_test_db_dirs()
    yield
    delete_test_db_dirs()


class TestMultiProcessLevelDB:
    store_process_functions = [f_rocksdb, f_lmdb]

    @pytest.mark.parametrize("store_process_function", store_process_functions)
    def test_multiprocessing_db(self, store_process_function):
        p1 = Process(target=store_process_function, args=("prop1",))
        p1.start()

        p2 = Process(target=store_process_function, args=("prop2",))
        p2.start()

        p1.join()
        p2.join()

        # RocksDB supports multiprocessing.
        assert p1.exitcode == 0
        assert p2.exitcode == 0
