class DropboxNoCredentials(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CacheMutex(Exception):
    def __init__(self, lock, value):
        self.value = value
        self.lock = lock
    def __str__(self):
        return repr(self.lock)
