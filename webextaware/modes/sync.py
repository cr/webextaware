# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from .runmode import RunMode
import webextaware.amo as amo
import webextaware.metadata as md


logger = logging.getLogger(__name__)


class SyncMode(RunMode):
    """
    Mode to update local AMO metadata and web extension file cache
    """

    name = "sync"
    help = "update local AMO metadata and web extension file cache"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("-n", "--nometa",
                            help="do not update metadata, just download extensions",
                            action="store_true",
                            default=False)

    def run(self):
        if self.args.nometa:
            logger.warning("Using cached AMO metadata, not updating")
        else:
            logger.info("Downloading current metadata set from AMO")
            self.meta = md.Metadata(filename=md.get_metadata_file(self.args),
                                    data=amo.download_metadata(), webext_only=True)
            self.meta.save()
        logger.info("Downloaded metadata set contains %d web extensions" % len(self.meta))
        logger.info("Downloading missing web extensions")
        amo.update_files(self.meta, self.files)
        return 0
