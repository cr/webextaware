# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os

from .runmode import RunMode


logger = logging.getLogger(__name__)


class UnzipMode(RunMode):
    """
    Mode to extract extensions
    """

    name = "unzip"
    help = "extract extensions"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("-o", "--outdir",
                            action="store",
                            default="ext",
                            help="root path for extraction (default: $PWD/ext)")

        parser.add_argument("selectors",
                            metavar="selector",
                            nargs="+",
                            help="AMO IDs, extension IDs, regexp, `orphans`, `all`")

    def run(self):
        exts = self.db.get_ext(self.args.selectors)
        if len(exts) == 0:
            logger.warning("No results")
            return 10

        for amo_id in exts:
            for ext_id in exts[amo_id]:
                unzip_path = os.path.join(self.args.outdir, str(amo_id), ext_id)
                os.makedirs(unzip_path, exist_ok=True)
                with exts[amo_id][ext_id] as ext:
                    ext.unzip(unzip_path)
                print(unzip_path)

        return 0
