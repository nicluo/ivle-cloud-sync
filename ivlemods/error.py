class DropboxNoCredentials(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class DropboxExceedQuota(Exception):
    def __init__(self, file_size, quota):
        self.file_size = file_size 
	self.quota = quota
    def __str__(self):
        return 'User has run out of Dropbox space'

class CacheMutex(Exception):
    def __init__(self, lock, value):
        self.value = value
        self.lock = lock
    def __str__(self):
        return repr(self.lock)

class FolderNotSynced(Exception):
    def __init__(self, user_id, file_id, folder_name):
        self.user_id = user_id
        self.file_id = file_id 
        self.folder_name = folder_name
    def __str__(self):
        return repr(self.user_id)
