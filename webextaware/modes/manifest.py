# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import sys

from .runmode import RunMode


logger = logging.getLogger(__name__)


class MetadataMode(RunMode):
    """
    Mode to query AMO and web extension IDs
    """

    name = "manifest"
    help = "print manifests as JSON"

    @staticmethod
    def setup_args(parser):
        parser.add_argument("-r", "--raw",
                            action="store_true",
                            help="dump raw manifests instead of digested JSON")

        parser.add_argument("-t", "--traverse",
                            action="store_true",
                            help="use a grep-friendly output format")

        parser.add_argument("selectors",
                            metavar="selector",
                            nargs="+",
                            help="AMO IDs, extension IDs, regexp, `orphans`, `all`")

    @staticmethod
    def check_args(args):
        global logger
        if args.raw and args.traverse:
            logger.critical("Cannot combine `--raw` and `--traverse`")
            return False
        return True

    def run(self):
        global logger

        exts = self.db.get_ext(self.args.selectors)
        if len(exts) == 0:
            logger.warning("No results")
            return 10

        if self.args.traverse:
            for amo_id in exts:
                for ext_id in exts[amo_id]:
                    ext = exts[amo_id][ext_id]
                    manifest = ext.manifest()
                    for line in manifest.traverse():
                        print("%s/%s/manifest.json%s" % (amo_id, ext_id, line))
            return 0

        if self.args.raw:
            for amo_id in exts:
                for ext_id in exts[amo_id]:
                    ext = exts[amo_id][ext_id]
                    manifest = ext.manifest()
                    sys.stdout.buffer.write(manifest.raw)
                    if not manifest.raw.endswith(b"\n"):
                        sys.stdout.buffer.write(b"\n")
            sys.stdout.flush()
            return 0

        manifests = {}
        for amo_id in exts:
            for ext_id in exts[amo_id]:
                if amo_id not in manifests:
                    manifests[amo_id] = {}
                ext = exts[amo_id][ext_id]
                try:
                    manifest = ext.manifest()
                except Exception as e:
                    logger.warning("Unable to parse extension manifest of %d - %s: %s" % (amo_id, ext_id, str(e)))
                    manifests[amo_id][ext_id] = None
                    continue
                manifests[amo_id][ext_id] = manifest.json

        print(json.dumps(manifests, sort_keys=True, indent=4))

        return 0
