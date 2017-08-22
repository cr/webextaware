# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
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
        parser.add_argument("modeargs",
                            metavar="modearg",
                            nargs="+",
                            action="append",
                            help="grep arguments")

    def run(self):
        where = []
        # For now assume every trailing numeric argument is an AMO ID
        for amo_id in reversed(self.args.modeargs[0]):
            if amo_id == "*":
                where.append("all")
                break
            elif amo_id.isdigit():
                where.append(int(amo_id))
            else:
                break
        grep_args = self.args.modeargs[0][:len(self.args.modeargs[0])-len(where)]
        if len(where) == 0:
            where = ["all"]
        logger.debug("Grep args: %s" % grep_args)
        logger.debug("Grepping in %s" % where)
        if "all" in where:
            search_ids = [ext["id"] for ext in self.meta]
        else:
            search_ids = where
        color = sys.stdout.isatty()
        for amo_id in search_ids:
            ext = self.meta.get_by_id(amo_id)
            if ext is not None:
                for f in ext["current_version"]["files"]:
                    hash_id = f["hash"].split(":")[1]
                    archive_path_ref = self.files.get(hash_id)
                    if archive_path_ref is None:
                        logger.warning("Missing zip file for ID %d, %s" % (amo_id, hash_id))
                    else:
                        we = webext.WebExtension(archive_path_ref.abspath)
                        try:
                            package_id = "%s%s%s" % (amo_id, os.path.sep, hash_id)
                            for line in we.grep(grep_args, color=color):
                                print(line.replace("<%= PACKAGE_ID %>", package_id))
                        finally:
                            we.cleanup()
        return 0
