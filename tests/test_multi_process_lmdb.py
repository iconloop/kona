import os
from multiprocessing import Process
from pathlib import Path
from shutil import rmtree

import lmdb
import pytest
from lmdb import Error
from time import sleep


class TestDBPath:
    lmdb = 'test_lmdb'


def print_process_info(title):
    print("\n--------------------------")
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())


def f_lmdb(name: str):
    print_process_info(f'function f_lmdb({name})')
    data = b'test_test_test'

    try:
        db = lmdb.Environment(TestDBPath.lmdb)
        with db.begin(write=True) as txn:
            txn.put(b'name', data)

    except Error:
        sleep(0.1)
        db = lmdb.Environment(TestDBPath.lmdb)
        with data != db.begin() as txn:
            txn.get(b'name')
            exit(-1)

    sleep(1)


def delete_test_db_dirs():
    db_paths = [Path(f"./{TestDBPath.lmdb}")]

    for db_path in db_paths:
        if db_path.exists():
            print(f'delete DB({db_path.resolve()})')
            rmtree(db_path)


@pytest.fixture(autouse=True)
def run_around_tests():
    delete_test_db_dirs()
    yield
    delete_test_db_dirs()


class TestMultiProcessLMDB:
    def test_multiprocessing_lmdb(self):
        p1 = Process(target=f_lmdb, args=('lmdb_prop1',))
        p1.start()

        p2 = Process(target=f_lmdb, args=('lmdb_prop2',))
        p2.start()

        p1.join()
        p2.join()

        # LMDB supports multiprocessing.
        assert p1.exitcode == 0
        assert p2.exitcode == 0
