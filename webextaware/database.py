# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import hashfs
import logging
import os
import re

from . import amo
from . import metadata as md
from . import webext as we


logger = logging.getLogger(__name__)


class Database(object):
    """Class for bundling high-level AMO and web extension functionality"""

    def __init__(self, args, files=None, metadata=None):
        self.args = args
        self.meta = metadata
        self.file_db = files

        if self.file_db is None:
            db_dir = os.path.join(self.args.workdir, "webext_data")
            if not os.path.isdir(db_dir):
                os.makedirs(db_dir)
            self.file_db = hashfs.HashFS(db_dir, depth=4, width=1, algorithm='sha256')

        if self.meta is None:
            self.meta = md.Metadata(filename=md.get_metadata_file(self.args))

    def sync(self):
        if self.args.nometa:
            logger.warning("Using cached AMO metadata, not updating")
        else:
            logger.info("Downloading current metadata set from AMO")
            self.meta = md.Metadata(filename=md.get_metadata_file(self.args),
                                    data=amo.download_metadata(), webext_only=True)
            self.meta.save()
        logger.info("Metadata set contains %d web extensions" % len(self.meta))
        logger.info("Downloading missing web extensions")
        amo.update_files(self.meta, self.file_db)

    def match(self, selectors):
        if type(selectors) is not list and type(selectors) is not tuple:
            selectors = [selectors]
        logger.debug("Matching for %s" % repr(selectors))

        selection = {}
        for selector in selectors:
            if selector == "all":
                for amo_ext in self.meta:
                    for ext_id in amo_ext.file_hashes():
                        if amo_ext.id not in selection:
                            selection[amo_ext.id] = set()
                        selection[amo_ext.id].add(ext_id)
            elif selector == "orphans":
                for file_path in self.file_db:
                    ext_id = self.file_db.get(file_path).id
                    if not self.meta.is_known_hash(ext_id):
                        if None not in selection:
                            selection[None] = set()
                        selection[None].add(ext_id)
            elif self.meta.is_known_id(selector):
                amo_ext = self.meta.get_by_id(selector)
                for ext_id in amo_ext.file_hashes():
                    if amo_ext.id not in selection:
                        selection[amo_ext.id] = set()
                    selection[amo_ext.id].add(ext_id)
            elif self.meta.is_known_hash(selector):
                amo_ext = self.meta.get_by_hash(selector)
                if amo_ext.id not in selection:
                    selection[amo_ext.id] = set()
                selection[amo_ext.id].add(selector)
            elif type(selector) is str and len(selector) == 64 and self.file_db.get(selector) is not None:
                amo_id = None
                if amo_id not in selection:
                    selection[amo_id] = set()
                selection[amo_id].add(selector)
            else:
                try:
                    m = re.compile(selector, re.IGNORECASE)
                except re.error:
                    logger.error("Invalid selector `%s`" % selector)
                    continue
                for amo_ext in self.meta:
                    if m.match(amo_ext.name) is not None:
                        for ext_id in amo_ext.file_hashes():
                            if amo_ext.id not in selection:
                                selection[amo_ext.id] = set()
                            selection[amo_ext.id].add(ext_id)

        return selection

    def get_meta(self, selectors):
        meta = {}
        match = self.match(selectors)
        for amo_id in match:
            meta[amo_id] = self.meta.get_by_id(amo_id)
        return meta

    def get_ext(self, selectors):
        extensions = {}
        match = self.match(selectors)
        for amo_id in match:
            for ext_id in match[amo_id]:
                file_ref = self.file_db.get(ext_id)
                if file_ref is None:
                    logger.warning("Cache miss for ID %s - %s" % (amo_id, ext_id))
                    continue
                file_path = file_ref.abspath
                if amo_id not in extensions:
                    extensions[amo_id] = {}
                extensions[amo_id][ext_id] = we.WebExtension(file_path)
        return extensions

    def grep(self, pattern, selectors=None):
        pass

    def unizp(self, directories=None, selectors=None):
        pass

    def scan(self, scanners=None, directories=None, selectors=None):
        pass
