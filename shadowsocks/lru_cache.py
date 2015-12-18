#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
一个基于LRU的Key-Value缓存
'''

from __future__ import absolute_import, division, print_function, \
    with_statement

import collections
import logging
import time


# this LRUCache is optimized for concurrency, not QPS
# n: concurrency, keys stored in the cache
# m: visits not timed out, proportional to QPS * timeout
# get & set is O(1), not O(n). thus we can support very large n
# TODO: if timeout or QPS is too large, then this cache is not very efficient,
#       as sweep() causes long pause

# 维基百科的介绍：lru缓存算法
# Least Recently Used (LRU)
# Discards the least recently used items first. This algorithm requires keeping track of what was used when, 
# which is expensive if one wants to make sure the algorithm always discards the least recently used item.
# General implementations of this technique require keeping "age bits" for cache-lines and 
# track the "Least Recently Used" cache-line based on age-bits. In such an implementation, 
# every time a cache-line is used, the age of all other cache-lines changes. 

# 用到了容器基类：易变序列，python3。。。理解为c++中的vector吧！
class LRUCache(collections.MutableMapping):
    """This class is not thread safe"""

    def __init__(self, timeout = 60, close_callback = None, *args, **kwargs):
        self.timeout = timeout
        self.close_callback = close_callback
        self._store = {}
        self._time_to_keys = collections.defaultdict(list)
        self._keys_to_last_time = {}
        self._last_visits = collections.deque()
        self.update(dict(*args, **kwargs))    # use the free update to set keys

    def __getitem__(self, key):
        # O(1)
        t = time.time()
        self._keys_to_last_time[key] = t
        self._time_to_keys[t].append(key)
        # 根据时间去清理
        self._last_visits.append(t)
        return self._store[key]

    def __setitem__(self, key, value):
        # O(1)
        t = time.time()
        self._keys_to_last_time[key] = t
        self._store[key] = value
        self._time_to_keys[t].append(key)
        self._last_visits.append(t)

    def __delitem__(self, key):
        # O(1)
        del self._store[key]
        del self._keys_to_last_time[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)


# 先找访问时间_last_visits中超出timeout的所有键
# 然后去找_time_to_keys，找出所有可能过期的键
# 因为最早访问时间访问过的键之后可能又访问了，所以要看_keys_to_last_time
# 找出那些没被访问过的，然后删除

    def sweep(self):
        # O(m)
        now = time.time()
        c = 0
        while len(self._last_visits) > 0:
            least = self._last_visits[0]
            if now - least <= self.timeout:
                break
            if self.close_callback is not None:
                for key in self._time_to_keys[least]:
                    if key in self._store:
                        if now - self._keys_to_last_time[key] > self.timeout:
                            value = self._store[key]
                            self.close_callback(value)
            
            # 最早的肯定是最前的
            for key in self._time_to_keys[least]:
                self._last_visits.popleft()
                if key in self._store:
                    if now - self._keys_to_last_time[key] > self.timeout:
                        del self._store[key]
                        del self._keys_to_last_time[key]
                        c += 1
            del self._time_to_keys[least]
        if c:
            logging.debug('%d keys swept' % c)


def test():
    c = LRUCache(timeout = 0.3)

    c['a'] = 1
    assert c['a'] == 1

    time.sleep(0.5)
    c.sweep()
    assert 'a' not in c

    c['a'] = 2
    c['b'] = 3
    time.sleep(0.2)
    c.sweep()
    assert c['a'] == 2
    assert c['b'] == 3

    time.sleep(0.2)
    c.sweep()
    c['b']
    time.sleep(0.2)
    c.sweep()
    assert 'a' not in c
    assert c['b'] == 3

    time.sleep(0.5)
    c.sweep()
    assert 'a' not in c
    assert 'b' not in c

if __name__ == '__main__':
    test()
