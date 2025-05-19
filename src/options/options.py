import os
import pathlib
import sys


class Options:
    pass


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return pathlib.Path(sys.executable).parent
    else:
        return pathlib.Path(__file__).parent.parent.parent


options = Options()
DEBUG = False
BASEDIR = get_base_dir()
SNAPS_FOLDER = os.path.join(BASEDIR, 'snaps')
