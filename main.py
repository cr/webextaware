#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import bz2
import coloredlogs
import hashfs
import logging
import os
import pprint

import amo
import webext


# Initialize coloredlogs
logger = logging.getLogger(__name__)
coloredlogs.DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s"
coloredlogs.install(level='INFO')

# Initialize pretty printer
pp = pprint.PrettyPrinter(indent=4)


def get_argparser():
    """
    Argument parsing
    :return: Argument parser object
    """
    home = os.path.expanduser('~')

    parser = argparse.ArgumentParser(prog="webextaware")
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.1a')
    parser.add_argument('-d', '--debug',
                        help='Enable debug',
                        action='store_true',
                        default=False)
    parser.add_argument('-w', '--workdir',
                        help='Path to working directory',
                        type=os.path.abspath,
                        action='store',
                        default='%s/.webextaware' % home)
    parser.add_argument('-i', '--ipython',
                        help='Drop into ipython shell',
                        action='store_true',
                        default=False)
    return parser


# This is the entry point used in setup.py
def main():
    global logger, pp

    parser = get_argparser()
    args = parser.parse_args()

    if args.debug:
        coloredlogs.install(level="DEBUG")

    logger.debug("Command arguments: %s" % args)

    metadata = amo.download_matedata(all_pages=False)
    hash_fs = hashfs.HashFS('webext_hashfs', depth=4, width=1, algorithm='sha256')
    # amo.update_files(metadata, hash_fs)

    import json

    with bz2.open("2017-04-25_dump.json.bz2", "w") as f:
        f.write(json.dumps(metadata).encode("utf-8"))

    print(len(metadata))

    logger.critical("RUNNING, NOT")

    e = webext.WebExtension("webext_hashfs//f/9/2/9/9ee56f1bced3ae17c01e1829165f192e7866321cf169b0d03803a596d7e7.zip")

    from IPython import embed
    embed()
