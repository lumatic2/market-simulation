import shutil
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class build_py(_build_py):
    def run(self):
        root = Path(__file__).parent
        src = root / 'SKILL.md'
        dst = root / 'market_simulation' / 'SKILL.md'
        if src.exists():
            shutil.copy(src, dst)
        super().run()


setup(cmdclass={'build_py': build_py})
