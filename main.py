#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import coloredlogs
import hashfs
import json
import logging
import os
import sys

import amo
import metadata as md
import scanner
import webext


# Initialize coloredlogs
logger = logging.getLogger(__name__)
coloredlogs.DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s"
coloredlogs.install(level='INFO')


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
    parser.add_argument('-n', '--noupdate',
                        help='Do not update metadata',
                        action='store_true',
                        default=False)
    parser.add_argument('mode',
                        nargs='?',
                        choices=['info', 'sync', 'metadata', 'manifests', 'stats', 'get', 'unzip',
                                 'scan', 'grep', 'ipython'],
                        help='run mode',
                        default='info')
    parser.add_argument('modeargs',
                        nargs='*',
                        action='append',
                        help='positional arguments for the run mode')
    return parser


# This is the entry point used in setup.py
def main():
    global logger

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
        meta = md.Metadata(filename=metadata_file)
        print("Local metadata set: %d entries" % len(meta))
        print("Local web extension set: %d files" % len(hash_fs))

    elif args.mode == "sync":
        if args.noupdate:
            logger.warning("Using stored metadata, not updating")
            meta = md.Metadata(filename=metadata_file)
        else:
            logger.info("Downloading current metadata set from AMO")
            meta = md.Metadata(filename=metadata_file, data=amo.download_matedata(), webext_only=True)
            meta.save()
        logger.info("Metadata set contains %d web extensions" % len(meta))
        logger.info("Downloading missing web extension files")
        amo.update_files(meta, hash_fs)

    elif args.mode == "metadata":
        meta = md.Metadata(filename=metadata_file)
        print(json.dumps(meta.json(), sort_keys=True, indent=4))

    elif args.mode == "manifest":
        if len(args.modeargs[0]) == 0:
            todo_list = hashfs
        else:
            todo_list = [int(id) for id in args.modeargs[0]]
        all_exts = []
        for ext_file in todo_list:
            ext = webext.WebExtension(hash_fs.get(ext_file).abspath)
            try:
                all_exts.append(ext.manifest().json)
            except json.decoder.JSONDecodeError:
                pass
        print(json.dumps(all_exts, indent=4))

    elif args.mode == "stats":
        meta = md.Metadata(filename=metadata_file)
        for ext in meta:
            e = md.Extension(ext)
            host_permissions, api_permissions = e.permissions()
            print("%d\t%s\t%d\t%d\t%s\t%s" % (
                ext["id"],
                e.name(),
                ext["average_daily_users"],
                ext["weekly_downloads"],
                host_permissions,
                api_permissions
            ))

    elif args.mode == "get":
        if len(args.modeargs[0]) == 0:
            logger.critical("Missing ID")
        meta = md.Metadata(filename=metadata_file)
        for id in args.modeargs[0]:
            id = int(id)
            ext = meta.by_id(id)
            if ext is not None:
                for f in ext["current_version"]["files"]:
                    hash = f["hash"].split(":")[1]
                    archive = hash_fs.get(hash).abspath
                    print(id, archive)

    elif args.mode == "unzip":
        if len(args.modeargs[0]) == 0:
            logger.critical("Missing ID")
        id = args.modeargs[0][0]
        if len(args.modeargs[0]) >= 2:
            folder = args.modeargs[0][1]
        else:
            folder = "/tmp"
        meta = md.Metadata(filename=metadata_file)
        if id == "all" or id == "*":
            ids = [ext["id"] for ext in meta]
        else:
            ids = [int(id)]
        for id in ids:
            ext = meta.by_id(id)
            archives = []
            if ext is not None:
                ext_unzip_folder = os.path.join(folder, "%d" % id)
                for f in ext["current_version"]["files"]:
                    hash = f["hash"].split(":")[1]
                    archive_path_ref = hash_fs.get(hash)
                    if archive_path_ref is None:
                        logger.warning("Missing zip file for ID %d, %s" % (id, hash))
                    else:
                        archive_path = archive_path_ref.abspath
                        unzip_path = os.path.join(ext_unzip_folder, hash)
                        os.makedirs(unzip_path)
                        archives.append(unzip_path)
                        ex = webext.WebExtension(archive_path)
                        ex.unzip(unzip_path)
            print(id, " ".join(archives))

    elif args.mode == "scan":
        if len(args.modeargs[0]) == 0:
            logger.critical("Missing ID")
        id = int(args.modeargs[0][0])
        meta = md.Metadata(filename=metadata_file)
        retire = scanner.RetireScanner()
        if not retire.dependencies():
            sys.exit(5)
        scanjs = scanner.ScanJSScanner()
        if not scanjs.dependencies():
            sys.exit(5)
        ext = meta.by_id(id)
        result = {"retire": {}, "scanjs": {}}
        if ext is not None:
            for f in ext["current_version"]["files"]:
                hash = f["hash"].split(":")[1]
                archive_path_ref = hash_fs.get(hash)
                if archive_path_ref is None:
                    logger.warning("Missing zip file for ID %d, %s" % (id, hash))
                else:
                    we = webext.WebExtension(archive_path_ref.abspath)
                    logger.info("Running retire.js scan on %d, %s" % (id, hash))
                    retire.scan(extension=we)
                    result["retire"][hash] = retire.result
                    logger.info("Running scanjs scan on %d, %s" % (id, hash))
                    scanjs.scan(extension=we)
                    result["scanjs"][hash] = scanjs.result
            print(json.dumps(result, indent=4))
        else:
            logger.critical("Missing extension for ID %d" % id)

    elif args.mode == "grep":
        if len(args.modeargs[0]) == 0:
            logger.critical("Missing grep arguments")
            sys.exit(-5)
        where = []
        # For now assume every trailing numeric argument is an AMO ID
        for id in reversed(args.modeargs[0]):
            if id == "*":
                where.append("all")
                break
            elif id.isdigit():
                where.append(int(id))
            else:
                break
        grep_args = args.modeargs[0][:len(args.modeargs[0])-len(where)]
        if len(where) == 0:
            where = ["all"]
        logger.debug("Grep args: %s" % grep_args)
        logger.debug("Grepping in %s" % where)
        meta = md.Metadata(filename=metadata_file)
        if "all" in where:
            search_ids = [ext["id"] for ext in meta]
        else:
            search_ids = where
        color = sys.stdout.isatty()
        for id in search_ids:
            ext = meta.by_id(id)
            if ext is not None:
                for f in ext["current_version"]["files"]:
                    hash = f["hash"].split(":")[1]
                    archive_path_ref = hash_fs.get(hash)
                    if archive_path_ref is None:
                        logger.warning("Missing zip file for ID %d, %s" % (id, hash))
                    else:
                        we = webext.WebExtension(archive_path_ref.abspath)
                        try:
                            package_id = "%s%s%s" % (id, os.path.sep, hash)
                            for line in we.grep(grep_args, color=color):
                                print(line.replace("<%= PACKAGE_ID %>", package_id))
                        finally:
                            we.cleanup()

    elif args.mode == "ipython":
        if len(args.modeargs[0]) == 0:
            logger.critical("Missing ID")
        meta = md.Metadata(filename=metadata_file)
        id = int(args.modeargs[0][0])
        ext = meta.by_id(id)
        files = []
        if ext is not None:
            for f in ext["current_version"]["files"]:
                hash = f["hash"].split(":")[1]
                archive = hash_fs.get(hash).abspath
                files.append(webext.WebExtension(archive))
        print("id: %d" % id)
        print("ext: %s" % ext)
        print("files: %s" % files)
        from IPython import embed
        embed()
