# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import bz2
import json
import logging


logger = logging.getLogger(__name__)


class Metadata(object):
    def __init__(self, filename=None, data=[], webext_only=False):
        self.__data = data
        self.__filename = filename
        self.__id_index = {}
        self.__hash_index = {}
        if len(data) == 0 and filename is not None:
            self.load(filename)
        if webext_only:
            filtered_data = []
            for ext in self.__data:
                for f in ext["current_version"]["files"]:
                    if f["is_webextension"]:
                        filtered_data.append(ext)
                        break
            self.__data = filtered_data
        self.generate_index()

    def data(self):
        return self.__data

    def load(self, metadata_filename):
        global logger
        try:
            with bz2.open(metadata_filename, "r") as f:
                logger.debug("Retrieving metadata state from `%s`" % metadata_filename)
                self.__data = json.load(f)
        except FileNotFoundError:
            logger.warning("No metadata state stored in `%s`" % metadata_filename)

    def save(self):
        global logger
        logger.debug("Writing metadata state to `%s`" % self.__filename)
        with bz2.open(self.__filename, "w") as f:
            f.write(json.dumps(self.__data).encode("utf-8"))

    def generate_index(self):
        self.__id_index = {}
        self.__hash_index = {}
        for ext in self.__data:
            self.__id_index[ext["id"]] = ext
            for file_data in ext["current_version"]["files"]:
                self.__hash_index[file_data["hash"].split(":")[1]] = ext

    def is_known_id(self, amo_id):
        try:
            amo_id = int(amo_id)
        except ValueError:
            return False
        return amo_id in self.__id_index

    def is_known_hash(self, hash_id):
        return hash_id in self.__hash_index

    def by_id(self, amo_id):
        try:
            amo_id = int(amo_id)
        except ValueError:
            return None
        if amo_id in self.__id_index:
            return self.__id_index[amo_id]
        else:
            return None

    def by_hash(self, hash_id):
        if hash_id in self.__hash_index:
            return self.__hash_index[hash_id]
        else:
            return None

    def id_to_hashes(self, amo_id):
        ext = self.by_id(amo_id)
        if ext is None:
            return None
        hashes = []
        for f in ext["current_version"]["files"]:
            if f["is_webextension"]:
                assert f["hash"].startswith("sha256:")
                hashes.append(f["hash"][7:])
        return hashes

    def hash_to_id(self, hash_id):
        return self.by_hash(hash_id)["id"]

    def __iter__(self):
        for ext in self.__data:
            for f in ext["current_version"]["files"]:
                if f["is_webextension"]:
                    yield ext
                    break

    def __len__(self):
        length = 0
        for _ in self:
            length += 1
        return length


class Extension(object):
    __language_priority = ['en-US', 'en-GB', 'uk', 'de', 'fr', 'pl', 'es', 'it', 'nl']

    def __init__(self, ext):
        self.__ext = ext

    def name(self):
        for lang in self.__language_priority:
            if lang in self.__ext["name"]:
                return self.__ext["name"][lang]
        lang = list(self.__ext["name"].keys())[0]
        return self.__ext["name"][lang]

    def permissions(self):
        aggregate_api_permissions = set()
        aggregate_host_permissions = set()
        for f in self.__ext["current_version"]["files"]:
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
