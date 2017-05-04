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
    def __init__(self, **kwargs):
        self.args = kwargs
        self.result = None
        self.scanner = "dummy"

    def dependencies(self):
        return True

    def scan(self, directory=None, extension=None):
        self.result = {}

    def is_scanning(self):
        return self.result is None

    def wait(self):
        while self.is_running():
            sleep(0.1)
        return self.result()


class RetireScanner(Scanner):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scanner = "retire"

    def dependencies(self):
        global logger
        self.result = {}
        if "retire_bin" in self.args:
            retire_bin = self.args["retire_bin"]
        else:
            try:
                cmd = ["npm", "bin"]
                node_bin_path = subprocess.check_output(cmd).decode("utf-8").split()[0]
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
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            logger.critical("Error running retire.js binary: `%s`" % str(e))
            return False
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
        cmd = [self.args["retire_bin"], "--outputformat", "json", "--path", unzip_dir]
        logger.debug("Running shell command `%s`" % " ".join(cmd))
        cmd_output = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE).stderr
        logger.debug("Shell command output: `%s`" % cmd_output)
        if rm_unzip_dir:
            shutil.rmtree(unzip_dir, ignore_errors=True)
        result = json.loads(cmd_output.decode("utf-8"))
        # Make file paths relative
        for r in result:
            if r["file"].startswith(unzip_dir):
                r["file"] = os.path.relpath(r["file"], start=unzip_dir)
        self.result = result


class ScanJSScanner(Scanner):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scanner = "scanjs"

    def dependencies(self):
        global logger
        self.result = {}
        if "eslint_bin" in self.args:
            eslint_bin = self.args["eslint_bin"]
        else:
            try:
                cmd = ["npm", "bin"]
                node_bin_path = subprocess.check_output(cmd).decode("utf-8").split()[0]
                cmd = ["npm", "root"]
                node_root_path = subprocess.check_output(cmd).decode("utf-8").split()[0]
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
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            logger.critical("Error running eslint binary: `%s`" % str(e))
            return False
        eslint_rc = os.path.join(node_root_path, "eslint-config-scanjs", ".eslintrc" )
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
        cmd_output = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
        logger.debug("Shell command output: `%s`" % cmd_output)
        if rm_unzip_dir:
            shutil.rmtree(unzip_dir, ignore_errors=True)
        if len(cmd_output) == 0:
            self.result = []
        else:
            result = json.loads(cmd_output.decode("utf-8"))
            for r in result:
                # Make file paths relative
                if r["filePath"].startswith(unzip_dir):
                    r["filePath"] = os.path.relpath(r["filePath"], start=unzip_dir)
                # Strip those massive `source` keys
                r["source"] = "/* stripped from results */"
                for m in r["messages"]:
                    m["source"] = "/* stripped from results */"
            self.result = result
