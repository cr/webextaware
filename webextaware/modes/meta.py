# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging

from .runmode import RunMode


logger = logging.getLogger(__name__)


class MetaaMode(RunMode):
    """
    Mode to query AMO and web extension IDs
    """

    name = "meta"
    help = "print AMO metadata objects as JSON"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("selectors",
                            metavar="selector",
                            nargs="*",
                            default=["all"],
                            help="AMO IDs, extension IDs, regexp, `orphans`, `all` (default)")

    def run(self):
        result = 0
        meta = self.db.get_meta(self.args.selectors)
        if len(meta) == 0:
            logger.warning("No results")
            result = 10
        print(json.dumps(meta, sort_keys=True, indent=4))
        return result
