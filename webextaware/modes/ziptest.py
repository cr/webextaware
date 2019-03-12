# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
from multiprocessing import Pool
import os
from pathlib import Path
import subprocess

from .runmode import RunMode

logger = logging.getLogger(__name__)


# Only written once before workers go working
# TODO: Find way to avoid globals by passing static arg to workers.
external_tester = None


def external_test(zipname):
    global external_tester

    cmd = [external_tester, zipname]
    logger.debug("Running shell command `%s`" % " ".join(cmd))
    p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, encoding="utf-8")
    if p.returncode == 0:
        return True, None, None
    elif p.returncode == 5:
        return False, str(p.stdout), str(p.stderr)
    else:
        return None, str(p.stdout), str(p.stderr)


def test_zip(zipname):
    logger.debug("Testing `%s`" % zipname)
    flag, stdout, stderr = external_test(zipname)
    return zipname, flag, stdout, stderr


def parallel_test(work_list):
    work_len = len(work_list)
    with Pool() as p:
        results = p.imap_unordered(test_zip, work_list)
        done = 0
        for result in results:
            done += 1
            if done % 500 == 0:
                logger.info("Progress: %d/%d (%.1f%%)" % (done, work_len, 100.0 * done / work_len))
            yield result


class RezipTestMode(RunMode):
    """
    Mode to for checking extensions against bug 1534483 / 1534573
    """

    name = "ziptest"
    help = "look for potential candidates for bug 1534483 / 1534573"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("-t", "--tester",
                            action="store",
                            help="path to binary that performs zip testing")
        parser.add_argument("selectors",
                            metavar="selectors",
                            nargs="+",
                            help="AMO IDs, extension IDs, regexp, `orphans`, `all`, or directories with extensions")

    def run(self):
        global external_tester

        if self.args.tester is None or not os.path.exists(self.args.tester):
            logger.critical("--tester must point to an executable binary")
            return 10

        external_tester = self.args.tester

        zip_list = []

        for s in self.args.selectors:
            if os.path.isdir(s):
                zip_list += map(str, Path(s).rglob("*.[zZxX][iIpP][pPiI]"))

            else:
                exts = self.db.get_ext([s])
                for amo_id in exts:
                    for ext_id in exts[amo_id]:
                        ext = exts[amo_id][ext_id]
                        zip_list.append(ext.filename)

        for zipname, flag, stdout, stderr in parallel_test(zip_list):
            if flag is None:
                logger.error("Tester failed for `%s`\nstderr:\n%s" % (zipname, stderr))
            elif not flag:
                logger.warning("Tester flagged `%s`\nstderr:\n%s\nstdout:\n%s" % (zipname, stderr, stdout))

        return 0
