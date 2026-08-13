from storage0 import Storage0
from storage1 import Storage1
from storage2 import Storage2
from storage3 import Storage3, Blob

import numpy as np
import os
import subprocess
import time

from storage_error import *

# ----- Disk generation -----

subprocess.run("bash create_disks.sh 4 > /dev/null 2>&1", shell=True)

disks = [f"disk{i}.bin" for i in range(4)]

# ----- Blob generation -----

# We want the total size to be ~ DISK_RATIO * size of disk

NUM_BLOBS = 5
DISK_RATIO = 1.1
sizes = np.random.randint(2**9, 2**19, NUM_BLOBS).astype(float)
sizes *= (os.path.getsize(disks[0]) / sizes.sum()) * DISK_RATIO
sizes = sizes.astype(int)

blobs = [Blob(size, np.random.bytes(size)) for size in sizes]

print(f"file size: {os.path.getsize(disks[0])}")
print(f"total blob size: {sum(sizes)}")

print(*[f"Blob {i}: {blob.size}" for i, blob in enumerate(blobs)], sep="\n")

# ----- Random sequence generation -----

OPERATIONS = ["insert", "fetch", "delete"]
SEQUENCE_LENGTH = 10

def validate_sequence(sequence):
	scope = set()
	for operation, key, _ in sequence:
		match operation:
			case "insert": 
				if key in scope:
					return False
				scope.add(key)
			case "fetch":
				if key not in scope: 
					return False
			case "delete":
				if key not in scope: 
					return False
				scope.remove(key)
	return True

while True:
	valid_sequence = []
	for i in range(SEQUENCE_LENGTH):
		operation = np.random.choice(OPERATIONS)
		key = np.random.randint(0, NUM_BLOBS)
		blob = blobs[key]
		valid_sequence.append([operation, key, blob])
	if validate_sequence(valid_sequence):
		break

print(*valid_sequence, sep='\n')

def insert(storage, key, blob):
	result = storage.insert(key, blob)
	if isinstance(result, StorageError):
		result.display()
		raise RuntimeError()

def fetch(storage, key, reference):
	blob = storage.fetch(key)
	if isinstance(blob, StorageError):
		blob.display()
		raise RuntimeError()
	if blob.data != reference.data:
		with open("diff_file", "w+") as file:
			file.write("expected:\n")
			file.write(reference.data.hex())
			file.write("\ngot:\n")
			file.write(blob.data.hex())
		raise RuntimeError(f"fetch returned incorrect data; expected {len(reference.data)} bytes, got {len(blob.data)}")

def delete(storage, key):
	storage.delete(key)
	try_fetch = storage.fetch(key)
	if not isinstance(try_fetch, StorageError) or try_fetch.code != KEY_NOT_FOUND:
		raise RuntimeError("delete failed to... delete")
	
def play(storage, sequence, name=""):
	global blobs
	start = time.perf_counter_ns()
	for operation, key, blob in sequence:
		match operation:
			case "insert":
				insert(storage, key, blob)
			case "fetch":
				fetch(storage, key, blobs[key])
			case "delete":
				delete(storage, key)
	end = time.perf_counter_ns()
	if name:
		print(f"{name} succeeded in {format_ns(end - start)}!")

def format_ns(n):
	if n >= 1_000_000:
		return f"{n} ms"
	elif n >= 1_000:
		return f"{n} µs"
	else:
		return f"{n} ns"

storages = [
	Storage0(disks[0]),
	Storage1(disks[1]),
	# Storage2(disks[2]),
	# Storage3(disks[3]),
]

for i, storage in enumerate(storages):
	try:
		play(storage, valid_sequence, f"storage{i}")
	except RuntimeError:
		continue
			
		




