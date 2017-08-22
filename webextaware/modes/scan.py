# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import os
import pkg_resources as pkgr
import pynpm
import shutil

from .runmode import RunMode
from .. import scanner


logger = logging.getLogger(__name__)


class ScanMode(RunMode):
    """
    Mode to to run security scanners
    """

    name = "scan"
    help = "run security scanners on extensions"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("-s", "--scanner",
                            action="append",
                            choices=sorted(scanner.list_scanners().keys()),
                            help="scanner to use (`retire` or `scanjs`; default: all)")

        parser.add_argument("selectors",
                            metavar="selector",
                            nargs="+",
                            action="append",
                            help="AMO IDs, extension IDs, regexp, `all`, `orphans`")

    def run(self):
        node_dir = check_npm_install(self.args)
        if node_dir is None:
            return 5
        matches = self.db.match(self.args.selectors[0])
        if len(matches) == 0:
            logger.warning("No results")
            return 10

        scanners = []
        if len(self.args.scanner[0]) == 0:
            scanner_list = scanner.list_scanners()
        else:
            scanner_list = {}
            all_scanners = scanner.list_scanners()
            for scanner_name in self.args.scanner:
                if scanner_name in all_scanners:
                    scanner_list[scanner_name] = all_scanners[scanner_name]
        for scanner_name in scanner_list:
            scanner_instance = scanner_list[scanner_name](node_dir=node_dir)
            if not scanner_instance.dependencies():
                return 20
            scanners.append(scanner_instance)

        results = {}
        for amo_id in matches:
            for ext_id in matches[amo_id]:
                ext = self.db.get_ext(ext_id)[amo_id][ext_id]
                file_ref = self.files.get(ext_id)
                if file_ref is None:
                    logger.warning("Cache miss for ID %s - %s" % (amo_id, ext_id))
                    continue

                if amo_id not in results:
                    results[amo_id] = {}
                if ext_id not in results[amo_id]:
                    results[amo_id][ext_id] = {}

                for scanner_instance in scanners:
                    logger.info("Running %s scan on %d, %s" % (scanner_instance.name, amo_id, ext_id))
                    scanner_instance.scan(extension=ext)
                    results[amo_id][ext_id][scanner_instance.name] = scanner_instance.result

        print(json.dumps(results, indent=4))

        return 0


def check_npm_install(args):
    node_dir = os.path.join(args.workdir, "node")
    os.makedirs(node_dir, exist_ok=True)
    package_json = os.path.join(node_dir, "package.json")
    module_package_json = pkgr.resource_filename("webextaware", "package.json")
    if not os.path.exists(package_json) \
            or os.path.getmtime(package_json) < os.path.getmtime(module_package_json):
        shutil.copyfile(module_package_json, package_json)
        try:
            npm_pkg = pynpm.NPMPackage(os.path.abspath(package_json))
            npm_pkg.install()
        except FileNotFoundError:
            logger.critical("Node Package Manager not found")
            os.unlink(package_json)  # To trigger reinstall
            return None
    return node_dir
