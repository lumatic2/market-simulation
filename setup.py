import shutil
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class build_py(_build_py):
    def run(self):
        shutil.copy(Path(__file__).parent / 'SKILL.md',
                    Path(__file__).parent / 'market_simulation' / 'SKILL.md')
        super().run()


setup(cmdclass={'build_py': build_py})
