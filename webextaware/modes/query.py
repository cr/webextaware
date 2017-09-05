# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from .runmode import RunMode
from .. import webext as we


logger = logging.getLogger(__name__)


class QueryMode(RunMode):
    """
    Mode to query AMO and web extension IDs
    """

    name = "query"
    help = "query relations between AMO IDs and web extension IDs"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("ids",
                            metavar="selector",
                            nargs="+",
                            help="AMO IDs, extension IDs, regexp, `orphans`, `all`")

    def run(self):
        matches = self.db.match(self.args.ids)
        if len(matches) == 0:
            logger.warning("No results")
            return 10

        for amo_id in matches:
            for ext_id in matches[amo_id]:
                if amo_id is None:
                    # Orphans are not referenced in current metadata
                    ext = we.WebExtension(self.files.get(ext_id).abspath)
                    ext_name = ext.manifest()["name"]
                else:
                    ext = self.db.get_meta(amo_id)[amo_id]
                    ext_name = ext.name
                print("%s\t%s\t%s" % (repr(amo_id), ext_id, ext_name))

        return 0
