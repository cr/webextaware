# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from distutils.spawn import find_executable
from collections import OrderedDict
import fnmatch
import json
import jsoncfg
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile


logger = logging.getLogger(__name__)


class WebExtension(object):

    grep_exe = find_executable("grep")
    if grep_exe is None:
        grep_exe = find_executable("grep.exe")

    def __init__(self, filename):
        self.filename = filename
        self.unzip_folder = None
        self.unzip_folder_is_temp = False

    def __str__(self):
        manifest = self.manifest()
        return "<WebExtension[%s-%s]>" % (manifest["name"], manifest["version"])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cleanup()

    def _open_ZipFile(self):
        return zipfile.ZipFile(self.filename)

    def manifest(self):
        logger.debug("Preparing manifest for %s" % self.filename)
        with self._open_ZipFile() as z:
            manifest = z.read("manifest.json")
        return Manifest(manifest)

    def ls(self):
        with self._open_ZipFile() as z:
            return z.namelist()

    def unzip(self, unzip_folder=None):
        if self.unzip_folder is not None and os.path.isdir(self.unzip_folder):
            return self.unzip_folder
        if unzip_folder is None:
            self.unzip_folder = tempfile.mkdtemp(prefix="webextaware_unzip_")
            self.unzip_folder_is_temp = True
        else:
            self.unzip_folder = unzip_folder
            self.unzip_folder_is_temp = False
        os.makedirs(self.unzip_folder, exist_ok=True)
        with self._open_ZipFile() as z:
            z.extractall(self.unzip_folder)
        return self.unzip_folder

    def is_unzipped(self):
        return self.unzip_folder is not None

    def cleanup(self):
        if self.unzip_folder is not None and self.unzip_folder_is_temp:
            shutil.rmtree(self.unzip_folder)
            self.unzip_folder = None
            self.unzip_folder_is_temp = False

    def find(self, glob_pattern):
        matches = []
        for file_name in self.ls():
            if fnmatch.fnmatch(file_name, glob_pattern):
                matches.append(file_name)
        return matches

    def grep(self, regexp, grep_args=None, color=False):
        if self.grep_exe is None:
            logger.critical("Can't find the `grep` binary.")
            return None
        if grep_args is None:
            grep_args = []
        if color:
            color_arg = ["--color=always"]
        else:
            color_arg = ["--color=never"]
        folder = self.unzip()
        cmd = [self.grep_exe, "-E"] + [regexp] + grep_args + color_arg + ["-r", folder]
        logger.debug("Running shell command `%s`" % " ".join(cmd))
        grep_result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if grep_result.stderr is not None and len(grep_result.stderr) > 0:
            logger.warning("Shell command yielded errors: `%s`" % grep_result.stderr.decode("utf-8"))
        if grep_result.stdout is None or len(grep_result.stdout) == 0:
            return []
        results = []
        try:
            decoded_result = grep_result.stdout.decode("utf-8")
        except UnicodeDecodeError as err:
            logger.warning("Error decoding grep results in `%s`: %s" % (self.unzip_folder, err))
            return results
        for line in decoded_result.splitlines():
            if line.startswith(folder):
                results.append(line.replace(folder, "<%= PACKAGE_ID %>"))
            elif line.startswith("Binary file ") and line.endswith(" matches"):
                filename = line[12:-8]
                if not os.path.isfile(filename) or not filename.startswith(folder):
                    logger.warning("Unexpected grep output: `%s`" % line)
                results.append("%s: Binary file matches" % filename.replace(folder, "<%= PACKAGE_ID %>"))
        return results


class Manifest(object):

    def __init__(self, content):
        self.raw = content
        try:
            utf_content = content.decode('utf-8-sig')
        except UnicodeDecodeError as e:
            # This should not be happening, but AMO lists several
            # extensions with non-standard manifest encoding.
            logger.warning("Unicode error in manifest: %s: %s" % (repr(content), str(e)))
            self.json = None
            return

        try:
            self.json = json.loads(utf_content)
        except ValueError as e:
            # There is lots of broken JSON in the wild. Most are using comments,
            # so will retry with a more relaxed parser.
            self.json = None
            logger.debug("Manifest can't be regularly parsed: %s: %s" % (repr(utf_content), str(e)))

        if self.json is None:
            logger.debug("Retrying with relaxed parser")
            try:
                self.json = jsoncfg.loads(utf_content)
            except jsoncfg.parser.JSONConfigParserException as e:
                # Give up when even relaxed parsing does not work.
                logger.error("Manifest can't be parsed: %s" % str(e))
                self.json = None

    def traverse(self):
        if self.json is None:
            logger.warning("Manifest contains invalid JSON")
            return []
        return list(traverse(self.json))

    def __getitem__(self, item):
        if self.json is None:
            raise KeyError
        return self.json[item]

    def __contains__(self, item):
        if self.json is None:
            return False
        return item in self.json

    def __str__(self):
        return json.dumps(self.json, indent=4)


def traverse(obj, ptr=None, path=""):
    if ptr is None:
        ptr = obj
    if type(ptr) is dict or type(ptr) is OrderedDict:
        for key in ptr.keys():
            for line in traverse(obj, ptr=ptr[key], path="%s/%s" % (path, key)):
                yield line
    elif type(ptr) is list:
        for item in ptr:
            for line in traverse(obj, ptr=item, path=path):
                yield line
    else:
        yield ":".join([path, repr(ptr)])
