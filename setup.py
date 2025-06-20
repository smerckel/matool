"""
Part of matool.

Licensed under GPL, see the file COPYRIGHT

Lucas Merckelbach lucas.merckelbach@hzg.de
31 May 2011, Gulf of Biscay
"""

import sys
import matools
version=matools.__version__

from distutils.core import setup


if sys.platform.startswith("linux"):
    setup(name="matools",
          version=version,
          install_requires=['arrow'],
          packages = ["matools"],
          scripts = ["matool","ma_edit_server","ma_server.py"],
          author = "Lucas Merckelbach",
          author_email = "lucas.merckelbach@hzg.de",
          url = "dockserver0.hzg.de/software/software.html")
else:
    import py2exe
    setup(name="matools",
          version=version,
          packages = ["matools"],
          console = ["matool"]
          )


