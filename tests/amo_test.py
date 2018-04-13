# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import hashfs
from nose.tools import *
import os
import requests

import tests
from webextaware import amo


def test_amo_metadata_downloader():
    """AMO metadata downloader"""
    # Operates on data pre-downloaded by tests.__init__.setup_package()
    meta = tests.raw_meta
    assert_true(type(meta) is list and type(meta[0]) is dict, "delivers expected format")
    assert_equal(len(meta), 100, "delivers expected number of extensions")
    assert_true("id" in meta[0] and "current_version" in meta[0] and "files" in meta[0]["current_version"],
                "metadata entries have expected format")
    assert_true(meta[0]["current_version"]["files"][0]["hash"].startswith("sha256:"), "hashes are SHA256")


def test_amo_extension_downloader():
    """AMO extension downloader"""
    # Operates on data pre-downloaded by tests.__init__.setup_package()

    # Download AMO pages until they contain at least five web extension files
    all_extensions = set()
    for ext in tests.raw_meta:
        for f in ext["current_version"]["files"]:
            if f["is_webextension"]:
                h = f["hash"].split(":")[1]
                all_extensions.add(h)

    # See which extensions were actually downloaded
    downloaded_extensions = set()
    for f in tests.ext_db:
        addr = tests.ext_db.get(f)
        downloaded_extensions.add(addr.id)

    assert_true(len(downloaded_extensions) > 10, "extensions are downloaded")
    assert_true(all_extensions >= downloaded_extensions, "only extensions from metadata are downloaded")
    assert_true(len(downloaded_extensions) > 0.5 * len(all_extensions), "at least 50% of extensions are downloaded")
