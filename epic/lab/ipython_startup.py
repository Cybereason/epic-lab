"""Import all from this module in your ipython profile startup code to get epic-lab set up
"""
from .synccode import SyncCodeDownloadMonitor, setup_synccode_path
synccode_download_monitor = SyncCodeDownloadMonitor()


def synccode_check_for_updates(wait=False):
    synccode_download_monitor.check_for_updates(wait=wait)


synccode_check_for_updates()
setup_synccode_path()

from .pdb import install_as_default
install_as_default()

from .shorthand import *
