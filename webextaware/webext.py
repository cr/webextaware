# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import fnmatch
import json
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile


logger = logging.getLogger(__name__)


class WebExtension(object):

    def __init__(self, filename):
        self.zip = zipfile.ZipFile(filename)
        self.unzip_folder = None
        self.unzip_folder_is_temp = False

    def __str__(self):
        manifest = self.manifest()
        return "<WebExtension[%s-%s]>" % (manifest["name"], manifest["version"])

    def manifest(self):
        with self.zip.open("manifest.json", "r") as f:
            manifest = f.read()
        return Manifest(manifest)

    def ls(self):
        for zip_obj in self.zip.filelist:
            yield zip_obj.filename

    def zipped_files(self):
        for zip_obj in self.zip.filelist:
            filename = zip_obj.filename
            if not filename.endswith('/'):  # is not directory
                with self.zip.open(filename) as f:
                    yield f, zip_obj

    def extracted_files(self):
        pass

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
        self.zip.extractall(self.unzip_folder)
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

    def grep(self, grep_args, color=False):
        folder = self.unzip()
        if color:
            color_arg = ["--color=always"]
        else:
            color_arg = ["--color=never"]
        cmd = ["grep", "-E"] + color_arg + grep_args + ["-r", folder]
        logger.debug("Running shell command `%s`" % " ".join(cmd))
        grep_result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if grep_result.stderr is not None and len(grep_result.stderr) > 0:
            logger.warning("Shell command yielded errors: `%s`" % grep_result.stderr.decode("utf-8"))
        if grep_result.stdout is None or len(grep_result.stdout) == 0:
            return []
        results = []
        for line in grep_result.stdout.decode("utf-8").splitlines():
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

    def __getitem__(self, key):
        return self.json[key]

    def __str__(self):
        return json.dumps(self.json, indent=4)
