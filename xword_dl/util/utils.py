import os
import sys

import dateparser
import yaml

# This imports the anyascii module, which converts Unicode strings to
# plain ASCII. The puz format, however, can accept Latin1, which is a larger
# subset, so we implement a copy of the anyascii function that employs the
# same logic, but also leaves codepoints 128-255 untouched. Ideally the
# anyascii project might be updated to support setting an "ignored character"
# function handler so we wouldn't have to replicate the whole function.
import anyascii
def anyascii_latin1(string):
    from sys import intern
    from zlib import decompress, MAX_WBITS
    try:
        from importlib.resources import read_binary
    except ImportError:
        from pkgutil import get_data as read_binary

    result = []
    for char in string:
        codepoint = ord(char)
        if codepoint <= 255:
            result.append(char)
            continue
        blocknum = codepoint >> 8
        lo = codepoint & 0xff
        try:
            block = anyascii._blocks[blocknum]
        except KeyError:
            try:
                b = read_binary('anyascii._data', '%03x' % blocknum)
                s = decompress(b, -MAX_WBITS).decode('ascii')
                block = tuple(map(intern, s.split('\t')))
            except FileNotFoundError:
                block = ()
            anyascii._blocks[blocknum] = block
        if len(block) > lo:
            result.append(block[lo])
    return ''.join(result)

# Wrap the above in a cover function named unidecode to avoid having to change any callpoint code
def unidecode(inString):
    return anyascii_latin1(inString)

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

def join_bylines(l, and_word="&"):
    return ', '.join(l[:-1]) + f', {and_word} ' + l[-1] if len(l) > 2 else f' {and_word} '.join(l)

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
