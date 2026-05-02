import pathlib
import shutil
import sys


def install_skill():
    src = pathlib.Path(__file__).parent / 'SKILL.md'
    dst = pathlib.Path.home() / '.claude' / 'skills' / 'market-simulation.md'
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    print(f'Skill installed → {dst}')
    print('Restart your Claude Code session to activate.')


def main():
    if len(sys.argv) < 2 or sys.argv[1] != 'install-skill':
        print('Usage: market-simulation install-skill')
        sys.exit(1)
    install_skill()


if __name__ == '__main__':
    main()
