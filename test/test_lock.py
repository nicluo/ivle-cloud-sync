from __future__ import absolute_import

import unittest
import ivlemods.lock as lock
from ivlemods.error import CacheMutex

class TestRedisLockFunctions(unittest.TestCase):
    def setUp(self):
        self.key = 'locktest-key'
        self.set1 = 'locktest-group1'
        self.set2 = 'locktest-group2'

    def tearDown(self):
        lock.release_lock(self.key)
        lock.release_lock(self.key, set=self.set1)
        lock.release_lock(self.key, set=self.set2)

    def test_try_lock(self):
        lock.try_lock(self.key, 'test-lock')
        self.assertRaises(CacheMutex, lock.try_lock, self.key, 'test-lock')

    def test_release_lock(self):
        lock.try_lock(self.key, 'test-lock')
        self.assertRaises(CacheMutex, lock.try_lock, self.key, 'test-lock')
        lock.release_lock(self.key)
        lock.try_lock(self.key, 'test-lock')

    def test_try_lock_with_sets(self):
        lock.try_lock(self.key, 'test-lock', set=self.set1)
        lock.try_lock(self.key, 'test-lock', set=self.set2)
        self.assertRaises(CacheMutex, lock.try_lock, self.key, 'test-lock', set=self.set1)
        self.assertRaises(CacheMutex, lock.try_lock, self.key, 'test-lock', set=self.set2)

    def test_release_lock_with_sets(self):
        lock.try_lock(self.key, 'test-lock', set=self.set1)
        lock.try_lock(self.key, 'test-lock', set=self.set2)
        self.assertRaises(CacheMutex, lock.try_lock, self.key, 'test-lock', set=self.set1)
        self.assertRaises(CacheMutex, lock.try_lock, self.key, 'test-lock', set=self.set2)
        lock.release_lock(self.key, set=self.set1)
        lock.release_lock(self.key, set=self.set2)
        lock.try_lock(self.key, 'test-lock', set=self.set1)
        lock.try_lock(self.key, 'test-lock', set=self.set2)


if __name__ == '__main__':
    unittest.main()



