# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
from multiprocessing import Pool
import os
import pkg_resources as pkgr
import pynpm
import shutil

from .runmode import RunMode
from .. import scanner
from ..webext import traverse


logger = logging.getLogger(__name__)


class LibsMode(RunMode):
    """
    Mode to detect libraries and frameworks
    """

    name = "libs"
    help = "collect statistics on libraries and frameworks"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("-e", "--perext",
                            action="store_true",
                            help="use web extension-centric output format")

        parser.add_argument("-t", "--traverse",
                            action="store_true",
                            help="produce a grep-friendly output format")

        parser.add_argument("-H", "--human",
                            action="store_true",
                            help="print human-readable output format")

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

        retire_instance = scanner.RetireScanner(node_dir=node_dir)
        if not retire_instance.dependencies():
            return 20

        work_list = [(amo_id, ext_id) for amo_id in matches for ext_id in matches[amo_id]]
        results = {}
        for amo_id, ext_id, result in parallel_scan(work_list, self, retire_instance):
            if amo_id not in results:
                results[amo_id] = {}
            if ext_id not in results[amo_id]:
                results[amo_id][ext_id] = {}
            results[amo_id][ext_id] = result

        if self.args.perext:
            if self.args.human:
                logger.warning("Human-readable output not implemented for per-extension results")
            # Remove entries with empty results
            for amo_id in results:
                for ext_id in results[amo_id]:
                    results[amo_id][ext_id] = list(filter(lambda r: "results" in r and len(r["results"]) > 0,
                                                          results[amo_id][ext_id]))
            if not self.args.traverse:
                print(json.dumps(results, indent=4))
            else:
                for line in traverse(results):
                    print(line.lstrip("/"))

        else:
            components = by_components(results)

            if not self.args.human:
                print(json.dumps(components, indent=4))

            else:
                # severity_rating = ["-", "low", "medium", "high"]
                aggregate = aggregate_counts(components)
                amo_count = len(matches)
                ext_count = sum([len(matches[amo_id]) for amo_id in matches])
                for component in sorted(aggregate.keys()):
                    for version in sorted(aggregate[component].keys()):
                        print("%40s\t%-15s\t%7d (%.1f%%)\t%7d (%.1f%%)" % (
                            component,
                            version,
                            aggregate[component][version]["amo_ids"],
                            aggregate[component][version]["amo_ids"] * 100.0 / amo_count,
                            aggregate[component][version]["ext_ids"],
                            aggregate[component][version]["ext_ids"] * 100.0 / ext_count
                        ))

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


def sub_versions(version):
    subs = version.split(".")
    for i in range(len(subs)):
        yield ".".join(subs[:i+1])


mp_mode = None
mp_scanner = None


def parallel_scan(work_list, mode, scanner_instance):
    global mp_mode, mp_scanner
    mp_mode = mode
    mp_scanner = scanner_instance
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
    global mp_mode, mp_scanner
    amo_id, ext_id = work_item
    try:
        ext = mp_mode.db.get_ext(ext_id)[amo_id][ext_id]
    except KeyError:
        logger.debug("Missing cache file for %s - %s" % (amo_id, ext_id))
        return amo_id, ext_id, None
    file_ref = mp_mode.files.get(ext_id)
    if file_ref is None:
        logger.warning("Cache miss for ID %d - %s" % (amo_id, ext_id))
        return amo_id, ext_id, None

    logger.debug("Running %s scan on %s, %s" % (mp_scanner.name, amo_id, ext_id))
    mp_scanner.scan(extension=ext, verbose=True)
    return amo_id, ext_id, mp_scanner.result


def by_components(results):
    components = {}
    for amo_id in results:
        for ext_id in results[amo_id]:
            if results[amo_id][ext_id] is None:
                continue
            for detection in results[amo_id][ext_id]:
                if "results" in detection:
                    # This is a regular result with `file` and `results` keys
                    for result in detection["results"]:
                        c_name = result["component"]
                        c_version = result["version"]
                        if c_name not in components:
                            components[c_name] = {}
                        component = components[c_name]
                        if c_version not in component:
                            component[c_version] = {}
                            component[c_version].update(result)
                            if "detection" in component[c_version]:
                                del component[c_version]["detection"]
                            component[c_version]["matches"] = {}
                        if amo_id not in component[c_version]["matches"]:
                            component[c_version]["matches"][amo_id] = {}
                        if ext_id not in component[c_version]["matches"][amo_id]:
                            component[c_version]["matches"][amo_id][ext_id] = []
                        component[c_version]["matches"][amo_id][ext_id].append(detection["file"])
                else:
                    # This is a file-less result with just `component` and `version`
                    for d in detection:
                        c_name = d["component"]
                        c_version = d["version"]
                        if c_name not in components:
                            components[c_name] = {}
                        if c_version not in components[c_name]:
                            components[c_name][c_version] = {}
                            components[c_name][c_version].update(d)
                            components[c_name][c_version]["matches"] = {}
                        if amo_id not in components[c_name][c_version]["matches"]:
                            components[c_name][c_version]["matches"][amo_id] = {}
                        if ext_id not in components[c_name][c_version]["matches"][amo_id]:
                            components[c_name][c_version]["matches"][amo_id][ext_id] = []
                        components[c_name][c_version]["matches"][amo_id][ext_id].append(None)
    return components


def aggregate_counts(components):
    aggregate = {}
    for c_name in components:
        aggregate[c_name] = {}
        for c_version in components[c_name]:
            for v in sub_versions(c_version):
                if v not in aggregate[c_name]:
                    aggregate[c_name][v] = {
                        "amo_ids": 0,
                        "ext_ids": 0
                    }
                for amo_id in components[c_name][c_version]["matches"]:
                    aggregate[c_name][v]["amo_ids"] += 1
                    aggregate[c_name][v]["ext_ids"] += \
                        len(components[c_name][c_version]["matches"][amo_id])
    return aggregate
