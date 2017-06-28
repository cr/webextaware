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
import pkg_resources as pkgr
import pynpm
import shutil
import sys

import webextaware.amo as amo
import webextaware.metadata as md
import webextaware.scanner as scanner
import webextaware.webext as webext


# Initialize coloredlogs
logger = logging.getLogger(__name__)
coloredlogs.DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s"
coloredlogs.install(level='INFO')


def get_argparser():
    """
    Argument parsing
    :return: Argument parser object
    """
    pkg_version = pkgr.require("webextaware")[0].version
    home = os.path.expanduser('~')

    parser = argparse.ArgumentParser(prog="webextaware")
    parser.add_argument('--version', action='version', version='%(prog)s ' + pkg_version)
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
                        choices=['info', 'query', 'sync', 'metadata', 'manifest', 'stats', 'get', 'unzip',
                                 'scan', 'grep', 'ipython'],
                        help='run mode',
                        default='info')
    parser.add_argument('modeargs',
                        nargs='*',
                        action='append',
                        help='positional arguments for the run mode')
    return parser


def check_npm_install(args):
    node_dir = os.path.join(args.workdir, "node")
    os.makedirs(node_dir, exist_ok=True)
    package_json = os.path.join(node_dir, "package.json")
    module_package_json = pkgr.resource_filename(__name__, "package.json")
    if not os.path.exists(package_json) \
            or os.path.getmtime(package_json) < os.path.getmtime(module_package_json):
        shutil.copyfile(module_package_json, package_json)
        try:
            npm_pkg = pynpm.NPMPackage(os.path.abspath(package_json))
            npm_pkg.install()
        except FileNotFoundError:
            logger.critical("Node Package Manager not found")
            os.unlink(package_json)  # To trigger reinstall
            return None
    return node_dir


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

    elif args.mode == "query":
        meta = md.Metadata(filename=metadata_file)
        for arg in args.modeargs[0]:
            if meta.is_known_id(arg):
                print("AMO ID %s is associated with %s" % (arg, " ".join(meta.id_to_hashes(arg))))
            elif meta.is_known_hash(arg):
                print("Hash %s belongs to AMO ID %d" % (arg, meta.hash_to_id(arg)))
            else:
                print("Unknown reference")

    elif args.mode == "sync":
        if args.noupdate:
            logger.warning("Using stored metadata, not updating")
            meta = md.Metadata(filename=metadata_file)
        else:
            logger.info("Downloading current metadata set from AMO")
            meta = md.Metadata(filename=metadata_file, data=amo.download_matedata(), webext_only=True)
            meta.save()
        logger.info("Metadata set contains %d web extensions" % len(meta))
        logger.info("Downloading web extensions")
        amo.update_files(meta, hash_fs)

    elif args.mode == "metadata":
        meta = md.Metadata(filename=metadata_file)
        if len(args.modeargs[0]) == 0 or "all" in args.modeargs[0]:
            print(json.dumps(meta.data(), sort_keys=True, indent=4))
        else:
            amo_ids = list(map(int, args.modeargs[0]))
            for metadata in meta:
                if metadata["id"] in amo_ids:
                    print(json.dumps(metadata, sort_keys=True, indent=4))

    elif args.mode == "manifest":
        meta = md.Metadata(filename=metadata_file)
        if len(args.modeargs[0]) == 0:
            todo_list = hashfs
        else:
            todo_list = args.modeargs[0]
        ext_todo = []
        for ext_id in todo_list:
            if meta.is_known_hash(ext_id):
                ext_todo.append(webext.WebExtension(hash_fs.get(ext_id).abspath))
            elif meta.is_known_id(ext_id):
                ext = meta.by_id(ext_id)
                for f in ext["current_version"]["files"]:
                    hash_id = f["hash"].split(":")[1]
                    archive_path_ref = hash_fs.get(hash_id)
                    if archive_path_ref is None:
                        logger.warning("Missing zip file for ID %d, %s" % (ext_id, hash_id))
                    else:
                        archive_path = archive_path_ref.abspath
                        ex = webext.WebExtension(archive_path)
                        ext_todo.append(ex)
            else:
                logger.warning("Unknown reference `%s`" % ext_id)
                continue

        for ext in ext_todo:
            try:
                print(ext.manifest())
            except json.decoder.JSONDecodeError:
                logger.warning("Manifest can't be decoded for extension")
                pass

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
        for amo_id in args.modeargs[0]:
            amo_id = int(amo_id)
            ext = meta.by_id(amo_id)
            if ext is not None:
                for f in ext["current_version"]["files"]:
                    hash_id = f["hash"].split(":")[1]
                    archive = hash_fs.get(hash_id).abspath
                    print(amo_id, archive)

    elif args.mode == "unzip":
        if len(args.modeargs[0]) == 0:
            logger.critical("Missing ID")
        amo_id = args.modeargs[0][0]
        if len(args.modeargs[0]) >= 2:
            folder = args.modeargs[0][1]
        else:
            folder = "/tmp"
        meta = md.Metadata(filename=metadata_file)
        if amo_id == "all" or amo_id == "*":
            ids = [ext["id"] for ext in meta]
        else:
            ids = [int(amo_id)]
        if len(ids) > 1:
            logger.info("Unzipping %d web extensions")
        for amo_id in ids:
            ext = meta.by_id(amo_id)
            archives = []
            if ext is not None:
                ext_unzip_folder = os.path.join(folder, "%d" % amo_id)
                for f in ext["current_version"]["files"]:
                    hash_id = f["hash"].split(":")[1]
                    archive_path_ref = hash_fs.get(hash_id)
                    if archive_path_ref is None:
                        logger.warning("Missing zip file for ID %d, %s" % (amo_id, hash_id))
                    else:
                        archive_path = archive_path_ref.abspath
                        unzip_path = os.path.join(ext_unzip_folder, hash_id)
                        os.makedirs(unzip_path, exist_ok=True)
                        archives.append(unzip_path)
                        ex = webext.WebExtension(archive_path)
                        ex.unzip(unzip_path)
            print(amo_id, " ".join(archives))

    elif args.mode == "scan":
        node_dir = check_npm_install(args)
        if node_dir is None:
            sys.exit(5)
        if len(args.modeargs[0]) == 0:
            logger.critical("Missing ID")
        amo_id = int(args.modeargs[0][0])
        meta = md.Metadata(filename=metadata_file)
        retire = scanner.RetireScanner(node_dir=node_dir)
        if not retire.dependencies():
            sys.exit(5)
        scanjs = scanner.ScanJSScanner(node_dir=node_dir)
        if not scanjs.dependencies():
            sys.exit(5)
        ext = meta.by_id(amo_id)
        result = {"retire": {}, "scanjs": {}}
        if ext is not None:
            for f in ext["current_version"]["files"]:
                hash_id = f["hash"].split(":")[1]
                archive_path_ref = hash_fs.get(hash_id)
                if archive_path_ref is None:
                    logger.warning("Missing zip file for ID %d, %s" % (amo_id, hash_id))
                else:
                    we = webext.WebExtension(archive_path_ref.abspath)
                    logger.info("Running retire.js scan on %d, %s" % (amo_id, hash_id))
                    retire.scan(extension=we)
                    result["retire"][hash_id] = retire.result
                    logger.info("Running scanjs scan on %d, %s" % (amo_id, hash_id))
                    scanjs.scan(extension=we)
                    result["scanjs"][hash_id] = scanjs.result
            print(json.dumps(result, indent=4))
        else:
            logger.critical("Missing extension for ID %d" % amo_id)

    elif args.mode == "grep":
        if len(args.modeargs[0]) == 0:
            logger.critical("Missing grep arguments")
            sys.exit(-5)
        where = []
        # For now assume every trailing numeric argument is an AMO ID
        for amo_id in reversed(args.modeargs[0]):
            if amo_id == "*":
                where.append("all")
                break
            elif amo_id.isdigit():
                where.append(int(amo_id))
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
        for amo_id in search_ids:
            ext = meta.by_id(amo_id)
            if ext is not None:
                for f in ext["current_version"]["files"]:
                    hash_id = f["hash"].split(":")[1]
                    archive_path_ref = hash_fs.get(hash_id)
                    if archive_path_ref is None:
                        logger.warning("Missing zip file for ID %d, %s" % (amo_id, hash_id))
                    else:
                        we = webext.WebExtension(archive_path_ref.abspath)
                        try:
                            package_id = "%s%s%s" % (amo_id, os.path.sep, hash_id)
                            for line in we.grep(grep_args, color=color):
                                print(line.replace("<%= PACKAGE_ID %>", package_id))
                        finally:
                            we.cleanup()

    elif args.mode == "ipython":
        import pprint
        meta = md.Metadata(filename=metadata_file)
        if len(args.modeargs[0]) == 0:
            logger.critical("Missing ID")
        else:
            amo_id = int(args.modeargs[0][0])
            ext = meta.by_id(amo_id)
            files = []
            if ext is not None:
                for f in ext["current_version"]["files"]:
                    hash_id = f["hash"].split(":")[1]
                    archive = hash_fs.get(hash_id).abspath
                    files.append(webext.WebExtension(archive))
                    print(json.dumps(ext, indent=4))
            print("\nNumber files for extension ID: %d" % len(files))
            print("file = %s\n" % [str(f) for f in files])
        from IPython import embed
        embed()
