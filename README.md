# kona

It is a project created to manage various key-value stores.  
Currently, only RocksDB is supported, but we will continue to increase the number of key-value stores that can be
supported.

## Prerequisite

- python 3.7.5

## Supported Key-Value Store

- RocksDB v6.26.1
- LMDB v0.9.x

## Installation

~~~
$ pip install kona
~~~

## Example

~~~python
from kona.key_value_store import KeyValueStore

db = KeyValueStore.new(
    'file://./key_value_store_test_database',
    store_type='rocksdb',
    create_if_missing=True
)

db.put(b'foo', b'bar')
print(db.get(b'foo'))
db.close()
db.destroy_store()

# Result
# b'bar'
~~~

### Batch
You can write to DataBase at a specific point in time using `WriteBatch()`.
~~~python
from kona.key_value_store import KeyValueStore

db = KeyValueStore.new(
    'file://./key_value_store_test_database',
    store_type='rocksdb',
    create_if_missing=True
)

batch = db.WriteBatch()

batch.put(b'test_key_1', b'test_value_1')
batch.put(b'test_key_2', b'test_value_2')

batch.write()

print(db.get(b'test_key_1'))
print(db.get(b'test_key_2'))

db.destroy_store()

# Result
# b'test_value_1'
# b'test_value_2'
~~~

### CancelableBatch
You can cancel data written in batches using `CancelableWriteBatch()`.
~~~python
from kona.key_value_store import KeyValueStore

db = KeyValueStore.new(
    'file://./key_value_store_test_database',
    store_type='rocksdb',
    create_if_missing=True
)

test_items = {
    b'test_key_1': b'test_value_1',
    b'test_key_2': b'test_value_2',
    b'test_key_3': b'test_value_3',
    b'test_key_4': b'test_value_4',
    b'test_key_5': b'test_value_5',
}

for key, value in test_items.items():
    db.put(key, value)

cancelable_batch = db.CancelableWriteBatch()
cancelable_batch.put(b'cancelable_key_1', b'cancelable_value_1')
cancelable_batch.put(b'test_key_2', b'edited_test_value_2')
cancelable_batch.put(b'cancelable_key_2', b'cancelable_value_2')
cancelable_batch.put(b'test_key_4', b'edited_test_value_4')
cancelable_batch.write()

for key, value in db.Iterator():
    print(f'Before Cancel: key={key}, value={value}')

cancelable_batch.cancel()

for key, value in db.Iterator():
    print(f'After Cancel: key={key}, value={value}')

db.destroy_store()

# Before Cancel
# Before Cancel: key=b'cancelable_key_1', value=b'cancelable_value_1'
# Before Cancel: key=b'cancelable_key_2', value=b'cancelable_value_2'
# Before Cancel: key=b'test_key_1', value=b'test_value_1'
# Before Cancel: key=b'test_key_2', value=b'edited_test_value_2'
# Before Cancel: key=b'test_key_3', value=b'test_value_3'
# Before Cancel: key=b'test_key_4', value=b'edited_test_value_4'
# Before Cancel: key=b'test_key_5', value=b'test_value_5'

# After Cancel
# After Cancel: key=b'test_key_1', value=b'test_value_1'
# After Cancel: key=b'test_key_2', value=b'test_value_2'
# After Cancel: key=b'test_key_3', value=b'test_value_3'
# After Cancel: key=b'test_key_4', value=b'test_value_4'
# After Cancel: key=b'test_key_5', value=b'test_value_5'
~~~
