# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import os
import shutil
import subprocess
import tempfile
from time import sleep


logger = logging.getLogger(__name__)


class Scanner(object):

    name = "dummy"

    def __init__(self, **kwargs):
        self.args = kwargs
        self.result = None

    def dependencies(self):
        return True

    def scan(self, directory=None, extension=None):
        self.result = {}

    def is_scanning(self):
        return self.result is None

    def wait(self):
        while self.is_scanning():
            sleep(0.1)
        return self.result()


def __subclasses_of(cls):
    sub_classes = cls.__subclasses__()
    sub_sub_classes = []
    for sub_cls in sub_classes:
        sub_sub_classes += __subclasses_of(sub_cls)
    return sub_classes + sub_sub_classes


def list_scanners():
    """Return a list of all scanners"""
    return dict([(scanner.name, scanner) for scanner in __subclasses_of(Scanner)])


class RetireScanner(Scanner):

    name = "retire"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def dependencies(self):
        global logger
        self.result = {}
        if "retire_bin" in self.args:
            retire_bin = self.args["retire_bin"]
        else:
            try:
                cmd = ["npm", "bin"]
                node_bin_path = subprocess.check_output(cmd, cwd=self.args["node_dir"]).decode("utf-8").split()[0]
            except FileNotFoundError:
                logger.critical("Node Package Manager not found")
                return False
            retire_bin = os.path.join(node_bin_path, "retire")
            logger.debug("Checking `%s`" % retire_bin)
            if not os.path.isfile(retire_bin):
                if os.path.isfile("%s.exe" % retire_bin):
                    retire_bin = "%s.exe" % retire_bin
                    logger.debug("Checking `%s`" % retire_bin)
                else:
                    logger.critical("Unable to find retire.js binary")
                    return False
            self.args["retire_bin"] = retire_bin
        logger.debug("Using retire.js binary at `%s`" % retire_bin)
        cmd = [retire_bin, "--version"]
        try:
            subprocess.check_call(cmd, cwd=self.args["node_dir"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            logger.critical("Error running retire.js binary: `%s`" % str(e))
            return False
        return True

    def scan(self, unzip_dir=None, extension=None, verbose=False):
        global logger
        if unzip_dir is None:
            unzip_dir = tempfile.mkdtemp()
            rm_unzip_dir = True
        else:
            rm_unzip_dir = False
        if extension is not None:
            extension.unzip(unzip_dir)
        cmd = [self.args["retire_bin"], "--outputformat", "json", "--outputpath", "/dev/stdout",
               "--js", "--jspath", unzip_dir]
        if verbose:
            # List all detected frameworks, not just vulnerable
            cmd.append("--verbose")
        logger.debug("Running shell command `%s`" % " ".join(cmd))
        cmd_output = subprocess.run(cmd, cwd=self.args["node_dir"], check=False, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL).stdout
        logger.debug("Shell command output: `%s`" % cmd_output)
        if rm_unzip_dir:
            shutil.rmtree(unzip_dir, ignore_errors=True)
        try:
            result = json.loads(cmd_output.decode("utf-8"))
        except json.decoder.JSONDecodeError:
            logger.warning("retirejs call failed, probably due to network failure")
            logger.warning("Failing output is `%s`" % cmd_output)
            self.result = None
            return
        # Make file paths relative
        for r in result:
            if "file" not in r:
                continue
            if r["file"].startswith(unzip_dir):
                r["file"] = os.path.relpath(r["file"], start=unzip_dir)
        self.result = result


class ScanJSScanner(Scanner):

    name = "scanjs"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def dependencies(self):
        global logger
        try:
            cmd = ["npm", "root"]
            node_root_path = subprocess.check_output(cmd, cwd=self.args["node_dir"]).decode("utf-8").split()[0]
        except FileNotFoundError:
            logger.critical("Node Package Manager not found")
            return False
        if "eslint_bin" in self.args:
            eslint_bin = self.args["eslint_bin"]
        else:
            try:
                cmd = ["npm", "bin"]
                node_bin_path = subprocess.check_output(cmd, cwd=self.args["node_dir"]).decode("utf-8").split()[0]
            except FileNotFoundError:
                logger.critical("Node Package Manager not found")
                return False
            eslint_bin = os.path.join(node_bin_path, "eslint")
            logger.debug("Checking `%s`" % eslint_bin)
            if not os.path.isfile(eslint_bin):
                logger.debug("Checking `%s`" % eslint_bin)
                if os.path.isfile("%s.exe" % eslint_bin):
                    eslint_bin = "%s.exe" % eslint_bin
                else:
                    logger.critical("Unable to find eslint binary")
                    return False
            self.args["eslint_bin"] = eslint_bin
        logger.debug("Using eslint binary at `%s`" % eslint_bin)
        cmd = [eslint_bin, "--version"]
        try:
            subprocess.check_call(cmd, cwd=self.args["node_dir"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            logger.critical("Error running eslint binary: `%s`" % str(e))
            return False
        eslint_rc = os.path.join(node_root_path, "eslint-config-scanjs", ".eslintrc")
        logger.debug("Checking `%s`" % eslint_rc)
        if not os.path.isfile(eslint_rc):
            logger.critical("You must install the `eslint-plugin-scanjs-rules` node module")
            return False
        self.args["eslint_rc"] = eslint_rc
        logger.debug("Using scanjs config at `%s`" % eslint_rc)
        return True

    def scan(self, unzip_dir=None, extension=None):
        global logger
        if unzip_dir is None:
            unzip_dir = tempfile.mkdtemp()
            rm_unzip_dir = True
        else:
            rm_unzip_dir = False
        if extension is not None:
            extension.unzip(unzip_dir)
        cmd = [self.args["eslint_bin"],
               "--no-eslintrc",
               "--no-inline-config",
               "--ignore-pattern", "__MACOSX",
               "--quiet",  # suppresses warnings
               "-c", self.args["eslint_rc"],
               "-f", "json",
               unzip_dir]
        logger.debug("Running shell command `%s`" % " ".join(cmd))
        cmd_output = subprocess.run(cmd, cwd=self.args["node_dir"], check=False, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL).stdout
        logger.debug("Shell command output: `%s`" % cmd_output)
        if rm_unzip_dir:
            shutil.rmtree(unzip_dir, ignore_errors=True)
        if len(cmd_output) == 0:
            self.result = None
        else:
            try:
                result = json.loads(cmd_output.decode("utf-8"))
            except json.decoder.JSONDecodeError as err:
                logger.error("Failed to decode eslint output: %s" % str(err))
                logger.error("Failing output: %s" % cmd_output)
                self.result = None
                return

            for r in result:
                # Make file paths relative
                if r["filePath"].startswith(unzip_dir):
                    r["filePath"] = os.path.relpath(r["filePath"], start=unzip_dir)
                # Strip those massive `source` keys
                r["source"] = "/* stripped from results */"
                for m in r["messages"]:
                    m["source"] = "/* stripped from results */"
            self.result = result
