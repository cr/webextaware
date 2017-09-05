# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import logging
from multiprocessing import Pool
import os
import sys

from .runmode import RunMode
from .. import webext


logger = logging.getLogger(__name__)


class GrepMode(RunMode):
    """
    Mode to search for patterns in extension content
    """

    name = "grep"
    help = "search extension content for pattern"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("regexp",
                            action="store",
                            help="regular expression for `grep -E`")

        parser.add_argument("selectors",
                            metavar="selector",
                            nargs="*",
                            default=["all"],
                            help="AMO IDs, extension IDs, regexp, `orphans`, `all` (default)")

        parser.add_argument('grepargs',
                            nargs=argparse.REMAINDER,
                            help="additional arguments for `grep -E`")

    def setup(self):
        if not super().setup():
            return False
        if webext.WebExtension.grep_exe is None:
            logger.critical("Missing `grep` binary")
            return False
        logger.debug("Using `%s` for grepping" % webext.WebExtension.grep_exe)
        return True

    def run(self):
        matches = self.db.match(self.args.selectors)
        if len(matches) == 0:
            logger.warning("No results")
            return 10

        work_list = [(amo_id, ext_id) for amo_id in matches for ext_id in matches[amo_id]]
        for amo_id, ext_id, lines in parallel_grep(work_list, self):
            if lines is None:
                continue
            for line in lines:
                print(line)

        return 0


mp_mode = None


def parallel_grep(work_list, mode):
    global mp_mode
    mp_mode = mode
    work_len = len(work_list)
    with Pool() as p:
        results = p.imap_unordered(grep, work_list)
        done = 0
        for result in results:
            done += 1
            if done % 500 == 0:
                logger.info("Progress: %d/%d (%.1f%%)" % (done, work_len, 100.0 * done / work_len))
            yield result


def grep(work_item):
    global mp_mode
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

    logger.debug("Grepping in %s, %s" % (amo_id, ext_id))
    lines = []
    try:
        package_id = "%s%s%s" % (amo_id, os.path.sep, ext_id)
        for line in ext.grep(mp_mode.args.regexp, mp_mode.args.grepargs, color=sys.stdout.isatty()):
            lines.append(line.replace("<%= PACKAGE_ID %>", package_id))
    finally:
        ext.cleanup()
    return amo_id, ext_id, lines
