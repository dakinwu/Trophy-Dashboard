import os
import time

from app.core.cache import FileCache


def test_save_then_load_hits_within_ttl(tmp_path):
    cache = FileCache(tmp_path)
    cache.save("profile/testuser", {"a": 1})
    assert cache.load("profile/testuser", ttl_seconds=1000) == {"a": 1}


def test_load_miss_when_absent(tmp_path):
    cache = FileCache(tmp_path)
    assert cache.load("profile/nobody", ttl_seconds=1000) is None


def test_load_miss_when_expired(tmp_path):
    cache = FileCache(tmp_path)
    cache.save("profile/testuser", {"a": 1})
    # Backdate the file's mtime by 2 hours.
    path = cache._path("profile/testuser")
    old = time.time() - 7200
    os.utime(path, (old, old))
    assert cache.load("profile/testuser", ttl_seconds=3600) is None


def test_key_with_slash_is_namespaced(tmp_path):
    cache = FileCache(tmp_path)
    cache.save("enrichment/hltb/god-of-war", {"main": 20})
    assert cache.load("enrichment/hltb/god-of-war", ttl_seconds=1000) == {"main": 20}
