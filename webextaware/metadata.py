# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import bz2
import json
import logging
import os


logger = logging.getLogger(__name__)


def get_metadata_file(args):
    return os.path.join(args.workdir, "amo_metadata.json.bz2")


def create_directory_path(amo_id, ext_id, base=None):
    if base is None:
        return os.path.join(amo_id, ext_id)
    else:
        return os.path.join(base, amo_id, ext_id)


class Metadata(object):
    def __init__(self, filename=None, data=None, webext_only=True):
        self.__ext = []
        if data is not None:
            for e in data:
                ext = Extension(e)
                if ext.is_webextension():
                    self.__ext.append(ext)
        self.__filename = filename
        self.__hash_index = {}
        self.__id_index = {}
        if data is None and filename is not None:
            self.load(filename)
        if webext_only:
            self.__ext = list(filter(lambda ex: ex.is_webextension(), self.__ext))
        self.generate_index()

    def raw_data(self):
        return self.__ext

    def load(self, metadata_filename):
        global logger
        self.__ext = []
        try:
            with bz2.open(metadata_filename, "r") as f:
                logger.debug("Retrieving metadata state from `%s`" % metadata_filename)
                for e in json.load(f):
                    self.__ext.append(Extension(e))
        except FileNotFoundError:
            logger.warning("No metadata state stored in `%s`" % metadata_filename)

    def save(self):
        global logger
        logger.debug("Writing metadata state to `%s`" % self.__filename)
        with bz2.open(self.__filename, "w") as f:
            f.write(json.dumps(self.__ext).encode("utf-8"))

    def generate_index(self):
        self.__id_index = {}
        self.__hash_index = {}
        for ext in self.__ext:
            self.__id_index[ext.id] = ext
            for h in ext.file_hashes():
                self.__hash_index[h] = ext

    def is_known_id(self, amo_id):
        try:
            amo_id = int(amo_id)
        except (ValueError, TypeError):
            return False
        return amo_id in self.__id_index

    def is_known_hash(self, hash_id):
        return hash_id in self.__hash_index

    def get_by_id(self, amo_id):
        try:
            amo_id = int(amo_id)
        except (ValueError, TypeError):
            return None
        if amo_id in self.__id_index:
            return self.__id_index[amo_id]
        else:
            return None

    def get_by_hash(self, hash_id):
        if hash_id in self.__hash_index:
            return self.__hash_index[hash_id]
        else:
            return None

    def get(self, amo_or_hash_id):
        if self.is_known_id(amo_or_hash_id):
            return self.get_by_id(amo_or_hash_id)
        elif self.is_known_hash(amo_or_hash_id):
            return self.get_by_hash(amo_or_hash_id)
        else:
            return None

    def id_to_hashes(self, amo_id):
        ext = self.get_by_id(amo_id)
        if ext is None:
            return None
        return [h for h in ext.file_hashes()]

    def hash_to_id(self, hash_id):
        return self.get_by_hash(hash_id).id

    def __iter__(self):
        for ext in self.__ext:
            yield ext

    def __len__(self):
        return len(self.__ext)

    def iter_files(self):
        for ext in self:
            for f in ext.files:
                yield f


class Extension(dict):
    __language_priority = ['en-US', 'en-GB', 'uk', 'de', 'fr', 'pl', 'es', 'it', 'nl']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def id(self):
        return self["id"]

    @property
    def name(self):
        for lang in self.__language_priority:
            if lang in self["name"]:
                return self["name"][lang]
        lang = list(self["name"].keys())[0]
        return self["name"][lang]

    @property
    def permissions(self):
        aggregate_api_permissions = set()
        aggregate_host_permissions = set()
        for f in self["current_version"]["files"]:
            for p in f["permissions"]:
                if "/" in p or ":" in p or "<" in p:
                    aggregate_host_permissions.add(p)
                else:
                    aggregate_api_permissions.add(p)
        if len(aggregate_host_permissions) == 0:
            aggregate_host_permissions = None
        if len(aggregate_api_permissions) == 0:
            aggregate_api_permissions = None
        return aggregate_host_permissions, aggregate_api_permissions

    def is_webextension(self):
        if "current_version" not in self:
            return False
        for f in self["current_version"]["files"]:
            if f["is_webextension"]:
                return True
        return False

    def files(self, webext_only=True):
        if "current_version" not in self or "files" not in self["current_version"]:
            return
        for f in self["current_version"]["files"]:
            if f["is_webextension"] or not webext_only:
                yield f

    def file_hashes(self, webext_only=True):
        for f in self.files(webext_only=webext_only):
            yield f["hash"].split(":")[1]

    def __iter__(self):
        return self.files()
