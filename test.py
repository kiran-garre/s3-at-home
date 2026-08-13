from storage0 import Storage0
from storage1 import Storage1
from storage2 import Storage2
from storage3 import Storage3, Blob
import subprocess

import numpy as np
import os

# ----- Disk generation -----

subprocess.run("bash create_disks.sh 4", shell=True)

disks = [f"disk{i}.bin" for i in range(4)]

# ----- Blob generation -----

NUM_BLOBS = 5
sizes = np.random.randint(2**9, 2**19, NUM_BLOBS).astype(float)
sizes *= (os.path.getsize(disks[0]) / sizes.sum())
sizes = sizes.astype(int)

blobs = [Blob(size, np.random.bytes(size)) for size in sizes]

# ----- Sequence generation -----

OPERATIONS = ["insert", "fetch", "delete"]
SEQUENCE_LENGTH = 5

def validate_sequence(sequence):
	scope = set()
	for operation, key, _ in sequence:
		match operation:
			case "insert": 
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
	sequence = []
	for i in range(SEQUENCE_LENGTH):
		operation = np.random.choice(OPERATIONS)
		key = np.random.randint(0, NUM_BLOBS)
		blob = blobs[key]
		sequence.append([operation, key, blob])
	if validate_sequence(sequence):
		break

print(*sequence, sep='\n')

def insert(storage, key, blob):
	storage.insert(key, blob)

def fetch(storage, key, reference):
	data = storage.fetch(key)
	if data != reference.data:
		raise RuntimeError("fetch returned incorrect data")

def delete(storage, key):
	storage.delete(key)
	if storage.fetch(key) != None:
		raise RuntimeError("delete failed to... delete")

			
		




