from typing import Self
import json
from dataclasses import dataclass
from os import fsync

@dataclass
class LogEntry:
	key: str
	operation: str
	numbers: list[int]

	def serialize(self):
		return json.dumps(self.__dict__).encode("utf-8")

	# def pack(self):
	# 	key_bytes = self.key.encode("utf-8")
	# 	operation_bytes = self.operation.encode("utf-8")

	# 	header_format = "!3I" # big endian, 3 4 byte unsigned ints
	# 	header = struct.pack(header_format, len(key_bytes), len(operation_bytes), len(self.numbers))

	# 	body_format = format("!{}s{}s{}q", len(key_bytes), len(operation_bytes), len(self.numbers))
	# 	body = struct.pack(body_format, key_bytes, operation_bytes, *self.numbers)

	# 	return header + body
	
	# @staticmethod
	# def unpack(buffer) -> Self:
	# 	view = memoryview(buffer)
	# 	header_format = "!3I" # big endian, 3 4 byte unsigned ints
	# 	num_key_bytes, num_operation_bytes, num_numbers = struct.unpack(header_format, view[:12])

	# 	body_format = format("!{}s{}s{}q", num_key_bytes, num_operation_bytes, num_numbers)
	# 	body = struct.unpack(body_format, view[12:])

# def synced(func):
# 	def wrapper(self, *args, **kwargs):
# 		result = func(self, *args, **kwargs)
# 		self.handle.flush()
# 		fsync(self.handle.fileno())
# 		return result
# 	return wrapper

class Log:
	def __init__(self, log_disk_filename):
		self.handle = open(log_disk_filename, "a+b")

	# @synced
	def log(self, key, operation, numbers):
		entry = LogEntry(key, operation, numbers)
		self.handle.write(entry.serialize() + b"\n")

	# @synced
	def commit(self):
		self.handle.write(b"done\n")

	# @synced
	def checkpoint(self, state):
		serialized = json.dumps(state).encode("utf-8")
		self.handle.write(serialized + b"\n")

