import pathlib
import shutil
import sys


def install_skill():
    src = pathlib.Path(__file__).parent / 'SKILL.md'
    skill_dir = pathlib.Path.home() / '.claude' / 'skills' / 'market-simulation'
    dst = skill_dir / 'SKILL.md'
    if not src.exists():
        print(f'Error: skill file not found at {src}')
        print('Try reinstalling: pip install --upgrade market-simulation')
        sys.exit(1)
    try:
        # Remove legacy flat-file install if present
        legacy = skill_dir.parent / 'market-simulation.md'
        if legacy.exists():
            legacy.unlink()
        skill_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    except PermissionError:
        print(f'Permission denied: cannot write to {dst}')
        print(f'Manual install: copy {src} to {dst}')
        sys.exit(1)
    print(f'Skill installed: {dst}')
    print('Restart your Claude Code session to activate.')


def main():
    if len(sys.argv) < 2 or sys.argv[1] != 'install-skill':
        print('Usage: market-simulation install-skill')
        sys.exit(1)
    install_skill()


if __name__ == '__main__':
    main()
