class StorageError:
	def __init__(self, code=0, message=""):
		self.code = code
		self.message = message
	
	def display(self):
		print(f"{self.message} ({self.code})")


KEY_NOT_FOUND = 1
OUT_OF_SPACE = 2