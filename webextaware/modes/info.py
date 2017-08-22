# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from .runmode import RunMode


logger = logging.getLogger(__name__)


class InfoMode(RunMode):
    """
    Mode to provide info on the current state of webextaware
    """

    name = "info"
    help = "print info on state of local cache"

    def run(self):
        all_amo_ids = set()
        all_ext_ids = set()
        matches = self.db.match("all")
        for amo_id in matches:
            all_amo_ids.add(amo_id)
            for ext_id in matches[amo_id]:
                all_ext_ids.add(ext_id)
        amo_count = len(all_amo_ids)
        print("AMO IDs in local cache: %d" % amo_count)
        ext_count = len(all_ext_ids)
        print("Referenced extensions in cache: %d" % ext_count)
        file_count = len(self.files)
        print("Total files in cache: %d" % file_count)
        print("Orphans in cache: %d" % (file_count - ext_count))
        return 0
