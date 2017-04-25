#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import bz2
import coloredlogs
import hashfs
import json
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
                        default=os.path.join(home, '.webextaware'))
    parser.add_argument('mode',
                        nargs='?',
                        choices=['info', 'sync', 'metadata', 'manifests', 'stats', 'ipython'],
                        help='run mode',
                        default="info")
    return parser


# This is the entry point used in setup.py
def main():
    global logger, pp

    parser = get_argparser()
    args = parser.parse_args()

    if args.debug:
        coloredlogs.install(level="DEBUG")

    logger.debug("Command arguments: %s" % args)

    if not os.path.isdir(args.workdir):
        os.makedirs(args.workdir)

    webext_data_dir = os.path.join(args.workdir, "webext_data")
    if not os.path.isdir(webext_data_dir):
        os.makedirs(webext_data_dir)

    metadata_file = os.path.join(args.workdir, "amo_metadata.json.bz2")

    hash_fs = hashfs.HashFS(webext_data_dir, depth=4, width=1, algorithm='sha256')

    if args.mode == "info":
        try:
            with bz2.open(metadata_file, "r") as f:
                metadata = json.load(f)
        except FileNotFoundError:
            metadata = []
        print("Local metadata set: %d entries" % len(metadata))
        print("Local web extension set: %d files" % len(hash_fs))

    elif args.mode == "sync":
        logger.info("Downloading current metadata set from AMO")
        metadata = amo.download_matedata(maximum=1000)
        logger.info("Received metadata set containing %d web extensions" % len(metadata))
        with bz2.open(metadata_file, "w") as f:
            f.write(json.dumps(metadata).encode("utf-8"))
        logger.info("Downloading missing web extension files")
        amo.update_files(metadata, hash_fs)

    elif args.mode == "metadata":
        try:
            with bz2.open(metadata_file, "r") as f:
                metadata = json.load(f)
        except FileNotFoundError:
            metadata = []
        print(json.dumps(metadata, sort_keys=True, indent=4))

    elif args.mode == "manifests":
        all_exts = []
        for ext_file in hash_fs:
            ext = webext.WebExtension(hash_fs.get(ext_file).abspath)
            try:
                all_exts.append(ext.manifest().json)
            except json.decoder.JSONDecodeError:
                pass
        print(json.dumps(all_exts, sort_keys=True, indent=4))

    elif args.mode == "stats":
        try:
            with bz2.open(metadata_file, "r") as f:
                metadata = json.load(f)
        except FileNotFoundError:
            metadata = []
        for ext in metadata:
            print("%d\t%d\t%d\t%s" % (
                ext["id"], ext["average_daily_users"], ext["weekly_downloads"], json.dumps(ext["name"])
            ))

    elif args.mode == "ipython":
        test_ext_file = os.path.join(webext_data_dir,
                            "f/9/2/9/9ee56f1bced3ae17c01e1829165f192e7866321cf169b0d03803a596d7e7.zip")
        test_ext = webext.WebExtension(test_ext_file)
        from IPython import embed
        embed()
