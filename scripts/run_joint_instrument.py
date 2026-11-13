"""Explicit external-cache bootstrap shared with the strict joint CLI."""
from pathlib import Path
import argparse
import os
import stat
import sys

sys.dont_write_bytecode=True
if '--help' not in sys.argv and '-h' not in sys.argv:
    bootstrap=argparse.ArgumentParser(add_help=False,allow_abbrev=False)
    bootstrap.add_argument('--scratch-root',required=True)
    scratch,_=bootstrap.parse_known_args();root=Path(scratch.scratch_root)
    if not root.is_absolute(): raise ValueError('instrument CLI: absolute external scratch required')
    for parent in reversed((root,*root.parents)):
        info=parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT or (parent/'.git').exists()):
            raise ValueError('instrument CLI: ordinary external scratch required')
    os.environ.update(TEMP=str(root),TMP=str(root),NUMBA_CACHE_DIR=str(root/'numba'),MPLCONFIGDIR=str(root/'mpl'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data-pipeline'))
from joint_survey_instrument import main

if __name__=='__main__': raise SystemExit(main())
