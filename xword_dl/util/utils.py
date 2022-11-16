import os
import sys

import dateparser
import yaml

# This imports the _module_ unidecode, which converts Unicode strings to
# plain ASCII. The puz format, however, can accept Latin1, which is a larger
# subset. So the second line tells the module to leave codepoints 128-256
# untouched, then we import the _function_ unidecode.
import unidecode
unidecode.Cache[0] = [chr(c) if c > 127 else '' for c in range(256)]
from unidecode import unidecode

CONFIG_PATH = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
CONFIG_PATH = os.path.join(CONFIG_PATH, 'xword-dl/xword-dl.yaml')

if not os.path.exists(CONFIG_PATH):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    open(CONFIG_PATH, 'a').close()

class XWordDLException(Exception):
    pass


def save_puzzle(puzzle, filename):
    if not os.path.exists(filename):
        puzzle.save(filename)
        msg = ("Puzzle downloaded and saved as {}.".format(filename)
               if sys.stdout.isatty()
               else filename)
        print(msg)
    else:
        print("Not saving: a file named {} already exists.".format(filename),
              file=sys.stderr)


def remove_invalid_chars_from_filename(filename):
    invalid_chars = r'<>:"/\|?*'

    for char in invalid_chars:
        filename = filename.replace(char, '')

    return filename


def parse_date(entered_date):
    return dateparser.parse(entered_date, settings={'PREFER_DATES_FROM':'past'})


def parse_date_or_exit(entered_date):
    guessed_dt = parse_date(entered_date)

    if not guessed_dt:
        raise XWordDLException(
            'Unable to determine a date from "{}".'.format(entered_date))

    return guessed_dt


def update_config_file(heading, new_values_dict):
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f) or {}

    if heading not in config:
        config[heading] = {}

    config[heading].update(new_values_dict)

    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f)


def read_config_values(heading):
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f) or {}

    return config.get(heading, {})
