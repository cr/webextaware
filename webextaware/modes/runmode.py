# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import hashfs
import logging
import os

from .. import metadata as md
from .. import database as db


logger = logging.getLogger(__name__)


class RunMode(object):
    """
    Generic parent class for run mode implementations
    """

    name = "runmode"
    help = "Just a parent class for run modes"

    @staticmethod
    def setup_args(parser):
        """
        Add a subparser for the mode's specific arguments.

        This definition serves as default, but modes are free to
        override it.

        :param parser: parent argparser to add to
        :return: None
        """
        pass

    @staticmethod
    def check_args(args):
        """
        Validate mode args

        :param args: parsed arguments object
        :return: bool
        """
        del args
        return True

    def __init__(self, args, files=None, metadata=None, database=None):
        self.args = args

        if not os.path.isdir(args.workdir):
            os.makedirs(args.workdir)
        self.workdir = args.workdir

        self.files = files
        self.meta = metadata
        self.db = database

    def setup(self):
        """
        Performs all the setup shared among multiple runs of the mode.
        Put everything here that takes too long for __init__().
        :return: None
        """
        if self.files is None:
            db_dir = os.path.join(self.workdir, "webext_data")
            if not os.path.isdir(db_dir):
                os.makedirs(db_dir)
            self.files = hashfs.HashFS(db_dir, depth=4, width=1, algorithm='sha256')

        if self.meta is None:
            self.meta = md.Metadata(filename=md.get_metadata_file(self.args))

        if self.db is None:
            self.db = db.Database(self.args, files=self.files, metadata=self.meta)

        return True

    def run(self):
        """
        Executes the the steps that constitutes the actual run.
        Results are kept internally in the class instance.
        :return: None
        """
        pass

    def teardown(self):
        """
        Clean up steps required after runs were performed.
        :return: None
        """
        self.files = None
        self.meta = None
        self.db = None


def __subclasses_of(cls):
    sub_classes = cls.__subclasses__()
    sub_sub_classes = []
    for sub_cls in sub_classes:
        sub_sub_classes += __subclasses_of(sub_cls)
    return sub_classes + sub_sub_classes


def list_modes():
    """Return a list of all run modes"""
    return dict([(mode.name, mode) for mode in __subclasses_of(RunMode)])


def run(args):
    all_modes = list_modes()

    if args.mode is None:
        args.mode = "info"

    try:
        current_mode = all_modes[args.mode](args)
    except KeyError:
        logger.critical("Unknown run mode `%s`" % args.mode)
        return 5

    if not current_mode.check_args(args):
        return 5

    try:
        logger.debug("Running mode .setup()")
        if not current_mode.setup():
            logger.critical("Setup failed")
            return 10
        logger.debug("Running mode .run()")
        result = current_mode.run()

    except KeyboardInterrupt:
        logger.debug("Running mode .teardown()")
        current_mode.teardown()
        raise KeyboardInterrupt

    logger.debug("Running mode .teardown()")
    current_mode.teardown()

    return result
