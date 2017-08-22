# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import hashfs
import logging
import os
import shutil
import tempfile

from webextaware import amo
from webextaware import metadata as md


# Silence logging
logging.disable(logging.INFO)
logging.disable(logging.WARNING)
logging.disable(logging.ERROR)
logging.disable(logging.CRITICAL)


# Global variables for all tests
# CAVE: Must be accessed as tests.var to get the dynamic results written by setup_package().
#      `from test import var` on the module level always yields the default values, because
#      the import happens before setup is run.
ext_db = None
raw_meta = None
tmp_dir = None

# This is a bit of a hack to make nosetests "report" that the download is happening.
# This should have been in setup_package, but there it just makes for an awkward silence.
# CAVE: Need to make sure this is always run as the very first test. So far it is likely
# by its placement in the top file that contains tests.
def test_download_dummy():
    """Downloading live test data from AMO"""
    global ext_db, raw_meta, tmp_dir
    assert tmp_dir is not None
    raw_meta = amo.download_metadata(max_pages=2)
    hfs_tmp = os.path.join(tmp_dir, "hashfs_extension")
    ext_db = hashfs.HashFS(hfs_tmp, depth=4, width=1, algorithm='sha256')
    amo.update_files(raw_meta, ext_db)


def setup_package():
    """Set up shared test fixtures"""
    global ext_db, raw_meta, tmp_dir
    tmp_dir = tempfile.mkdtemp(prefix="webextaware_test_")


def teardown_package():
    """Tear down shared test fixtures"""
    global ext_db, raw_meta, tmp_dir
    ext_db = None
    raw_meta = None
    if tmp_dir is not None:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir = None


class ArgsMock(object):
    """
    Mock used for testing functionality that
    requires access to an args-style object.
    """
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __getattr__(self, attr):
        try:
            return self.kwargs[attr]
        except KeyError:
            return None
