# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from webextaware import webext as we


def test_webext_object(ext_db):
    """WebExtension object instantiation"""

    assert len(ext_db) > 0, "there are web extension files to work with"

    for file_name in ext_db:
        with we.WebExtension(file_name) as w:
            assert type(w) is we.WebExtension, "can be instantiated"
            assert "manifest.json" in w.ls(), "each has manifest.json"
            manifest = w.manifest()
            assert type(manifest) is we.Manifest, "can yield Manifest objects"
            zipped_names = w.ls()
            assert "manifest.json" in zipped_names, "manifest.json is among zipped_files"


def test_webext_manifest(ext_db):
    """WebExtension Manifest objects"""

    assert len(ext_db) > 0, "there are web extension files to work with"
    for file_name in ext_db:
        with we.WebExtension(file_name) as w:
            manifest = w.manifest()
            assert "manifest_version" in manifest and "version" in manifest and "name" in manifest, \
                "objects have mandatory fields"
            manifest_str = str(manifest)
            assert len(manifest_str) > 0, "string representation is not empty"

            re_manifest = json.loads(manifest_str)
            assert "manifest_version" in re_manifest and "version" in re_manifest and "name" in re_manifest, \
                "strings representations are valid JSON"
