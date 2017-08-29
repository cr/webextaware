# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import coloredlogs
import logging
import os
import pkg_resources as pkgr
import resource
import sys

from . import modes


# Initialize coloredlogs
logger = logging.getLogger(__name__)
coloredlogs.DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s"
coloredlogs.install(level="INFO")


def get_args(argv=None):
    """
    Argument parsing
    :return: Argument parser object
    """
    if argv is None:
        argv = sys.argv[1:]

    pkg_version = pkgr.require("webextaware")[0].version
    home = os.path.expanduser("~")

    parser = argparse.ArgumentParser(prog="webextaware")
    parser.add_argument("--version", action="version", version="%(prog)s " + pkg_version)

    parser.add_argument("-d", "--debug",
                        help="Enable debug",
                        action="store_true",
                        default=False)

    parser.add_argument("-w", "--workdir",
                        help="Path to working directory",
                        type=os.path.abspath,
                        action="store",
                        default=os.path.join(home, ".webextaware"))

    # Set up subparsers, one for each mode
    subparsers = parser.add_subparsers(help="run mode", dest="mode")
    modes_list = modes.list_modes()
    for mode_name in modes_list:
        mode_class = modes_list[mode_name]
        sub_parser = subparsers.add_parser(mode_name, help=mode_class.help)
        mode_class.setup_args(sub_parser)

    return parser.parse_args(argv)


# This is the entry point used in setup.py
def main():
    global logger

    args = get_args()

    if args.debug:
        coloredlogs.install(level="DEBUG")

    logger.debug("Command arguments: %s" % args)

    # Adjust file limits
    from_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
    (soft_limit, hard_limit) = from_limit
    soft_limit = min(10000, hard_limit)
    to_limit = (soft_limit, hard_limit)
    logger.debug("Raising open file limit from %s to %s" % (repr(from_limit), repr(to_limit)))
    resource.setrlimit(resource.RLIMIT_NOFILE, to_limit)

    try:
        result = modes.run(args)

    except KeyboardInterrupt:
        logger.critical("User abort")
        return 5

    if result != 0:
        logger.error("Command failed")
        return result
