

from log import Log


class DurableStorage:
	def __init__(self, storage, log: Log):
		self.storage = storage
		self.log = log

	def insert(self, key, blob):
		self.log.log(key, "insert", "no idea")
		self.storage.insert(key, blob)
		self.log.commit()

	def delete(self, key):
		self.log.log(key, "delete", "no idea")
		self.storage.delete(key)
		self.log.commit()

	def fetch(self, key):
		return self.storage.fetchkey()