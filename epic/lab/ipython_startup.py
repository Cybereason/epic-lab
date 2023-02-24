"""Import all from this module in your ipython profile startup code to get epic-lab set up
"""
from . import pdb as our_pdb
from .synccode import SyncCodeDownloadMonitor, setup_synccode_path

our_pdb.install_as_default()

synccode_download_monitor = SyncCodeDownloadMonitor()
synccode_check_for_updates = synccode_download_monitor.check_for_updates
synccode_check_for_updates()
setup_synccode_path()

from .shorthand import *  # noqa
