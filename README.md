# xword-dl

`xword-dl` is a command-line tool to download .puz files for online crossword puzzles from supported outlets or arbitrary URLs. For a supported outlet, you can easily download the latest puzzle, or specify one from the archives.

Currently, `xword-dl` supports:
* Atlantic
* Daily Beast
* LA Times
* New Yorker
* Newsday
* USA Today
* Universal
* Wall Street Journal
* Washington Post
* Vox

To download a puzzle, install `xword-dl` and run it on the command line.

## Installation

To install `xword-dl`, download or clone this repository from Github. From a terminal, simply running

```
python setup.py install --user
```

in the downloaded directory may be enough. 

But you probably want to install `xword-dl` and its dependencies in a dedicated virtual environment. I use `virtualenv` and `virtualenvwrapper` personally, but that's a matter of preference. If you're already feeling overwhelmed by the thought of managing Python packages, know you're not alone. The [official documentation is pretty good](https://packaging.python.org/tutorials/installing-packages/), but it's a hard problem, and it's not just you. If it's any consolation, learning how to use virtual environments today on something sort of frivolous like a crossword puzzle downloader will probably save you from serious headaches in the future when the stakes are higher.

If you are installing in a dedicated virtual environment, run the above command without the `--user` flag.

## Usage

Once installed, you can invoke `xword-dl`, providing the short code of the site from which to download. If you run `xword-dl` without providing a site code, it will print some usage instructions and then exit.

For example, to download the latest New Yorker puzzle, you could run:

```
xword-dl tny --latest
```

or simply:

```
xword-dl tny
```

To download the Newsday Saturday Stumper and save it as `stumper.puz`, you could enter:

```
xword-dl nd --date saturday --output stumper
```

You can also download puzzles that are embedded in AmuseLabs solvers or on supported sites by providing a URL, such as:

```
xword-dl https://rosswordpuzzles.com/2021/01/03/cover-up/
```

The resulting .puz file can be opened with [`cursewords`](https://github.com/thisisparker/cursewords) or any other puz file reader.
