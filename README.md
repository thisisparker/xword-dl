# xword-dl

`xword-dl` is a command-line tool to download .puz files for online crossword puzzles from supported outlets or arbitrary URLs. For a supported outlet, you can easily download the latest puzzle, or specify one from the archives.

Currently, `xword-dl` supports:
* Atlantic
* Daily Beast
* Los Angeles Times
* New York Times
* New Yorker
* Newsday
* USA Today
* Universal
* Wall Street Journal
* Washington Post
* Vox

To download a puzzle, install `xword-dl` and run it on the command line.

## Installation

The easiest way to install `xword-dl` is through `pip`. Install the latest version with:

```
pip install xword-dl
```

You can also install `xword-dl` by downloading or cloning this repository from Github. From a terminal, simply running

```
python setup.py install
```

in the downloaded directory may be enough.

But in either case, you probably want to install `xword-dl` and its dependencies in a dedicated virtual environment. I use `virtualenv` and `virtualenvwrapper` personally, but that's a matter of preference. If you're already feeling overwhelmed by the thought of managing Python packages, know you're not alone. The [official documentation is pretty good](https://packaging.python.org/tutorials/installing-packages/), but it's a hard problem, and it's not just you. If it's any consolation, learning how to use virtual environments today on something sort of frivolous like a crossword puzzle downloader will probably save you from serious headaches in the future when the stakes are higher.

## Usage

Once installed, you can invoke `xword-dl`, providing the short code of the site from which to download. If you run `xword-dl` without providing a site keyword, it will print some usage instructions and then exit.

For example, to download the latest Newsday puzzle, you could run:

```
xword-dl nd --latest
```

or simply

```
xword-dl nd
```

You can also download puzzles that are embedded in AmuseLabs solvers or on supported sites by providing a URL, such as:

```
xword-dl https://rosswordpuzzles.com/2021/01/03/cover-up/
```

In either case, the resulting .puz file can be opened with [`cursewords`](https://github.com/thisisparker/cursewords) or any other puz file reader.

### Specifying puzzle date

Some outlets allow specification of a puzzle to download by date using the `--date` or `-d` flag. For example, to download the Universal puzzle from September 22, 2021, you could run:

```
xword-dl uni --date 9/22/21
```

The argument provided after the flag is parsed pretty liberally, and you can use relative descriptors such as "yesterday" or  "monday".

### New York Times authentication

New York Times puzzles are only available to subscribers. Attempting to download with the `nyt` keyword without authentication will fail. To authenticate, run:

```
xword-dl nyt --authenticate
```

and you will be prompted for your New York Times username and password. (Those credentials can also be passed at runtime with the `--username` and `--password` flags.)

If authentication is successful, an authentication token will be stored in a config file. Once that token is stored, you can download puzzles with `xword-dl nyt`.
