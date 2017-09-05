# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from .runmode import RunMode


logger = logging.getLogger(__name__)


class GetMode(RunMode):
    """
    Mode to get associated files in cache
    """

    name = "get"
    help = "get associated files in cache"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("selectors",
                            metavar="selector",
                            nargs="+",
                            help="AMO IDs, extension IDs, regexp, `orphans`, `all`")

    def run(self):
        matches = self.db.match(self.args.selectors)
        if len(matches) == 0:
            logger.warning("No results")
            return 10

        for amo_id in matches:
            for ext_id in matches[amo_id]:
                file_ref = self.files.get(ext_id)
                if file_ref is None:
                    logger.warning("Cache miss for AMO ID %d file %s" % (amo_id, ext_id))
                    continue
                file_path = file_ref.abspath
                print("%s\t%s" % (repr(amo_id), file_path))

        return 0
