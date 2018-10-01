# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import *
import os

from webextaware import metadata as md


def test_metadata_object(tmpdir, raw_meta):
    """Metadata cache object instantiation"""
    md_file = tmpdir.join("md.bz2")
    meta = md.Metadata(data=raw_meta, filename=md_file)
    assert_true(type(meta) is md.Metadata, "has correct type")
    assert_true(len(meta) > 0 and len(meta) > 0.5 * len(raw_meta), "contains metadata on extensions")
    assert_false(os.path.isfile(md_file), "metadata cache file is only written on demand")
    meta.save()
    assert_true(os.path.isfile(md_file), "metadata cache file is written on demand")

    meta_again = md.Metadata(filename=md_file)
    assert_equal(len(meta), len(meta_again), "restores data from cache file")


def test_metadata_extensions(raw_meta):
    """Metadata extension objects"""
    meta = md.Metadata(data=raw_meta)
    for e in meta:
        assert_true(type(e) is md.Extension, "iterating yields Extension objects")
        assert_true(type(e.id) is int and 0 < e.id < 100000000, "iterating yields Extensions with AMO IDs")
        assert_true(type(e.name) is str and len(e.name) > 0, "extensions have names")
        host_perm, api_perm = e.permissions
        assert_true(type(host_perm) is set or host_perm is None, "host permissions come as sets or None")
        assert_true(type(api_perm) is set or api_perm is None, "api permissions come as sets or None")
        assert_true(e.is_webextension(), "there are only web extensions in cache")

        for f in e.files():
            assert_true("hash" in f and "url" in f, "extension files have hashes and URLs")
            assert_true(f["hash"].startswith("sha256:"), "hashes are sha256")

        for h in e.file_hashes():
            assert_true(type(h) is str and h.isalnum() and len(h) == 64, "file IDs look like SHA256 hashes")


def test_metadata_id_handling(raw_meta):
    """Metadata ID handling"""
    meta = md.Metadata(data=raw_meta)
    assert_true(len(meta) > 0, "there is metadata to work with")

    for e in meta:
        amo_id = e.id
        hashes = meta.id_to_hashes(amo_id)

        assert_true(meta.is_known_id(amo_id), "AMO IDs are recognized")
        ext_amo = meta.get_by_id(amo_id)
        ext_amo_get = meta.get(amo_id)
        assert_true(type(ext_amo) is md.Extension and type(ext_amo_get) is md.Extension, "can get by AMO IDs")
        assert_true(ext_amo.id == ext_amo_get.id == e.id, "gets yield identical results for identical AMO IDs")

        for hash_id in hashes:
            assert_true(meta.is_known_hash(hash_id), "hash IDs are recognized")
            ext_hash = meta.get_by_hash(hash_id)
            ext_hash_get = meta.get(hash_id)
            assert_true(type(ext_hash) is md.Extension and type(ext_hash_get) is md.Extension, "can get by hash IDs")
            assert_true(ext_hash.id == ext_hash_get.id == amo_id, "gets yield same result for same hash ID")
            assert_true(meta.hash_to_id(hash_id) == amo_id, "hash IDs resolve to extension")
            assert_true(hash_id in meta.id_to_hashes(amo_id), "hash IDs are associated with AMO ID")

        assert_true(type(ext_amo) is md.Extension and type(ext_hash) is md.Extension, "can get by AMO and hash ID")
        assert_true(type(ext_amo_get) is md.Extension and type(ext_hash_get) is md.Extension, "can get by any ID")
        assert_true(ext_amo.id == ext_hash.id == ext_amo_get.id == ext_hash_get.id, "get method yield same result")

    # Test failure cases
    # amo_id and hash_id still hold valid IDs
    assert_false(meta.is_known_id(hash_id), "invalid AMO IDs are rejected")
    assert_false(meta.is_known_hash(amo_id), "invalid hash IDs are rejected")
    assert_true(meta.get_by_id(hash_id) is None, "invalid AMO IDs yield None")
    assert_true(meta.get_by_hash(amo_id) is None, "invalid hash IDs yield None")
    assert_true(meta.get("invalid foo") is None, "invalid get yields None")
