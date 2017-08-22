# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import IPython as ipy
import json
import logging
import pprint

from .runmode import RunMode
from .. import amo
from .. import database as dbase
from .. import metadata as md
from .. import scanner
from .. import webext as we


logger = logging.getLogger(__name__)


class ShellMode(RunMode):
    """
    Mode to run an IPython shell
    """

    name = "shell"
    help = "drop into an IPython shell"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("selectors",
                            metavar="selector",
                            nargs="*",
                            action="append",
                            help="AMO IDs, extension IDs, regexp, `all`, `orphans`")

    def run(self):

        if len(self.args.selectors[0]) == 0:
            matches = self.db.match("all")
        else:
            matches = self.db.match(self.args.ids[0])

        # Just for convenience
        meta = self.meta
        files = self.files
        db = self.db

        ipy.embed()

        return 0
