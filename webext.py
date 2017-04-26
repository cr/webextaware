# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import zipfile


logger = logging.getLogger(__name__)


class WebExtension(object):

    def __init__(self, filename):
        self.zip = zipfile.ZipFile(filename)

    def manifest(self):
        with self.zip.open("manifest.json", "r") as f:
            manifest = f.read()
        return Manifest(manifest)

    def files(self):
        for zip_obj in self.zip.filelist:
            filename = zip_obj.filename
            if not filename.endswith('/'):  # is not directory
                with self.zip.open(filename) as f:
                    yield f, zip_obj

    def unzip(self, folder):
        self.zip.extractall(folder)


class Manifest(object):

    def __init__(self, content):
        try:
            self.json = json.loads(content.decode('utf-8-sig'))
        except ValueError as e:
            self.json = None
            logger.error("Manifest can't be parsed: %s" % content)
            raise e

    def traverse(self, ptr=None, path=u''):
        if ptr is None:
            ptr = self.json
        if type(ptr) is str:
            s = path + ': ' + ptr
            print(s)
        elif type(ptr) is dict:
            keys = ptr.keys()
            # keys.sort()
            for key in keys:
                self.traverse(ptr[key], path + '/' + key)

    def __str__(self):
        return json.dumps(self.json, indent=4)
