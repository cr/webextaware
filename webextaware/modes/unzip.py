# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import glob
import logging
import os
from shutil import rmtree

from .runmode import RunMode
from ..metadata import create_directory_path

logger = logging.getLogger(__name__)


class UnzipMode(RunMode):
    """
    Mode to extract extensions
    """

    name = "unzip"
    help = "extract extensions"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("-n", "--nooverwrite",
                            action="store_true",
                            help="do not overwrite existing extension directories")

        parser.add_argument("-o", "--outdir",
                            action="store",
                            default="ext",
                            help="root path for extraction (default: $PWD/ext)")

        parser.add_argument("-p", "--prune",
                            action="store_true",
                            help="delete obsolete (unreferenced) extensions from outdir")

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
                unzip_path = create_directory_path(str(amo_id), ext_id, base=self.args.outdir)
                logger.debug("Considering to unzip %d to %s" % (amo_id, unzip_path))
                try:
                    os.makedirs(unzip_path, exist_ok=False)
                except FileExistsError:
                    if self.args.nooverwrite:
                        logger.Info("Skipping existing directory %s" % unzip_path)
                        continue
                with exts[amo_id][ext_id] as ext:
                    ext.unzip(unzip_path)
                print(unzip_path)

        if self.args.prune:
            logger.info("Pruning orphans from output directory")
            for ext_id in self.db.get_ext("orphans")[0]:
                for match in glob.glob(create_directory_path("*", ext_id, base=self.args.outdir)):
                    logger.info("Pruning `%s`" % match)
                    rmtree(match)

        return 0
