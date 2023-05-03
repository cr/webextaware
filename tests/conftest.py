# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import hashfs
import pytest

from webextaware import amo
from webextaware import metadata as md


@pytest.fixture(scope="session")
def raw_meta():
    """Raw AMO metadata session fixture"""
    return amo.download_metadata(max_pages=2)


@pytest.fixture(scope="session")
def hfs_tmp(tmpdir_factory):
    """Session-wide temporary directory"""
    return tmpdir_factory.mktemp("hashfs_extension")


@pytest.fixture(scope="session")
def ext_db(raw_meta, hfs_tmp):
    edb = hashfs.HashFS(hfs_tmp, depth=4, width=1, algorithm='sha256')
    meta = md.Metadata(data=raw_meta)
    amo.update_files(meta, edb)
    return edb
