# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import csv
import logging
import sys

from .runmode import RunMode


logger = logging.getLogger(__name__)


class StatsMode(RunMode):
    """
    Mode to generate extension statistics
    """

    name = "stats"
    help = "print CSV of web extension statistics"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("-o", "--output",
                            help="file for CSV output (default: stdout)",
                            action="store",
                            default=None)

    def run(self):
        field_names = [
            "amo_id",
            "name",
            "average_daily_users",
            "weekly_downloads",
            "host_permissions",
            "api_permissions"
        ]
        output_file = None
        if self.args.output is None:
            csv_writer = csv.DictWriter(sys.stdout, fieldnames=field_names)
        else:
            output_file = open(self.args.output, "w")
            csv_writer = csv.DictWriter(output_file, fieldnames=field_names)
        csv_writer.writeheader()

        metas = self.db.get_meta("all")
        for amo_id in metas.keys():
            ext = metas[amo_id]
            host_permissions, api_permissions = ext.permissions
            csv_writer.writerow({
                "amo_id": ext.id,
                "name": ext.name,
                "average_daily_users": ext["average_daily_users"],
                "weekly_downloads": ext["weekly_downloads"],
                "host_permissions": host_permissions,
                "api_permissions": api_permissions
            })

        if self.args.output is None:
            sys.stdout.flush()
        else:
            output_file.close()

        return 0
