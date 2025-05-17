import os
import pathlib


class Options:
    pass

options = Options()
DEBUG = True
BASEDIR = pathlib.Path(__file__).parent.parent.parent
SNAPS_FOLDER = os.path.join(BASEDIR, 'snaps')
