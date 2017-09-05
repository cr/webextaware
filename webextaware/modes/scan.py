# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from multiprocessing import Pool
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
    Mode to run security scanners
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
                            nargs="*",
                            default=["all"],
                            help="AMO IDs, extension IDs, regexp, `orphans`, `all` (default)")

    def run(self):
        node_dir = check_npm_install(self.args)
        if node_dir is None:
            return 5
        matches = self.db.match(self.args.selectors)
        if len(matches) == 0:
            logger.warning("No results")
            return 10

        scanners = []
        if self.args.scanner is None or len(self.args.scanner[0]) == 0:
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

        work_list = [(amo_id, ext_id) for amo_id in matches for ext_id in matches[amo_id]]
        results = {}
        for amo_id, ext_id, result in parallel_scan(work_list, self, scanners):
            if amo_id not in results:
                results[amo_id] = {}
            if ext_id not in results[amo_id]:
                results[amo_id][ext_id] = {}
            results[amo_id][ext_id] = result

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


mp_mode = None
mp_scanners = None


def parallel_scan(work_list, mode, scanners):
    global mp_mode, mp_scanners
    mp_mode = mode
    mp_scanners = scanners
    work_len = len(work_list)
    with Pool() as p:
        results = p.imap_unordered(scan, work_list)
        done = 0
        for result in results:
            if done % 100 == 0:
                logger.info("Progress: %d/%d (%.1f%%)" % (done, work_len, 100.0 * done / work_len))
            done += 1
            yield result


def scan(work_item):
    global mp_mode, mp_scanners
    amo_id, ext_id = work_item
    try:
        ext = mp_mode.db.get_ext(ext_id)[amo_id][ext_id]
    except KeyError:
        logger.debug("Missing cache file for %d - %s" % (amo_id, ext_id))
        return amo_id, ext_id, None
    file_ref = mp_mode.files.get(ext_id)
    if file_ref is None:
        logger.warning("Cache miss for ID %d - %s" % (amo_id, ext_id))
        return amo_id, ext_id, None

    result = {}
    for scanner_instance in mp_scanners:
        logger.info("Running %s scan on %s, %s" % (scanner_instance.name, amo_id, ext_id))
        scanner_instance.scan(extension=ext)
        result[scanner_instance.name] = scanner_instance.result

    return amo_id, ext_id, result
