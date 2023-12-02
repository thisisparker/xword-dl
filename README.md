# xword-dl

`xword-dl` is a command-line tool to download .puz files for online crossword puzzles from supported outlets or arbitrary URLs with embedded crossword solvers. For a supported outlet, you can easily download the latest puzzle, or specify one from the archives.

Supported outlets:

|Outlet|Keyword|Download latest|Search by date|Search by URL|
|------|-------|:-------------:|:------------:|:-----------:|
|*Atlantic*|`atl`|✔️|✔️||
|*Crossword Club*|`club`|✔️|✔️|✔️|
|*The Daily Beast*|`db`|✔️|||
|*Der Standard*|`std`|✔️||✔️|
|*The Globe And Mail cryptic*|`tgam`|✔️|✔️|✔️|
|*Guardian Cryptic*|`grdc`|✔️||✔️|
|*Guardian Everyman*|`grde`|✔️||✔️|
|*Guardian Prize*|`grdp`|✔️||✔️|
|*Guardian Quick*|`grdq`|✔️||✔️|
|*Guardian Quiptic*|`grdu`|✔️||✔️|
|*Guardian Speedy*|`grds`|✔️||✔️|
|*Guardian Weekend*|`grdw`|✔️||✔️|
|*Los Angeles Times*|`lat`|✔️|✔️||
|*The McKinsey Crossword*|`mck`|✔️|✔️|✔️|
|*The Modern Crossword*|`mod`|✔️|✔️|✔️|
|*New York Times*|`nyt`|✔️|✔️|✔️|
|*New York Times Mini*|`nytm`|✔️|✔️|✔️|
|*New York Times Variety*|`nytv`||✔️||
|*The New Yorker*|`tny`|✔️|✔️|✔️|
|*Newsday*|`nd`|✔️|✔️||
|*Simply Daily Puzzles*|`sdp`|✔️|✔️|✔️|
|*Simply Daily Puzzles Cryptic*|`sdpc`|✔️|✔️|✔️|
|*Simply Daily Puzzles Quick*|`sdpq`|✔️|✔️|✔️|
|*Universal*|`uni`|✔️|✔️||
|*USA Today*|`usa`|✔️|✔️||
|*Vox*|`vox`|✔️|||
|*Wall Street Journal*|`wsj`|✔️||✔️|
|*Washington Post*|`wp`|✔️|✔️||

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

The argument provided after the flag is parsed pretty liberally, and you can use relative descriptors such as "yesterday" or  "monday". Use quotes if your date contains spaces (such as "June 16, 2022").

### Specifying filenames

By default, files will be given a descriptive name based on puzzle metadata. If you want to specify a name for a given download, you can do so with the `-o` or `--output` flag. The following tokens are available:

|Token    |Value|
|---------|-----|
|`%outlet`|Outlet name|
|`%prefix`|Hardcoded outlet prefix|
|`%title` |Puzzle title|
|`%author`|Puzzle author|
|`%cmd`   |Puzzle outlet keyword|
|`%netloc`|Network location (domain and subdomain)|
|`date tokens`|[`strftime` tokens](https://strftime.org/)|

### Configuration file

When running `xword-dl`, a configuration file is created to store persistent settings. By default, this file is located at `~/.config/xword-dl/xword-dl.yaml`. You can manually edit this file to pass options to `xword-dl` at runtime.

Most settings are specified by the command keyword. For example, if you want to save *USA Today* puzzles in this format:

```
USA Today - By Brooke Husic  Ed. Erik Agard - Right Turns - 221115.puz
```

you can specify that by editing your config file to include the following lines:

```
usa:
  filename: '%prefix - %author - %title - %y%m%d'
```

In addition to command keywords, you can also use the keys `general` (to apply to all puzzles), `url` (to apply to embedded puzzles selected by URL at runtime) or with a given `netloc` (to apply to embedded puzzles at a given domain or subdomain).

### New York Times authentication

New York Times puzzles are only available to subscribers. Attempting to download with the `nyt` keyword without authentication will fail. To authenticate, run:

```
xword-dl nyt --authenticate
```

and you will be prompted for your New York Times username and password. (Those credentials can also be passed at runtime with the `--username` and `--password` flags.)

If authentication is successful, an authentication token will be stored in a config file. Once that token is stored, you can download puzzles with `xword-dl nyt`.

In some cases, the authentication may fail because of anti-automation efforts on New York Times servers. If the automatic authentication doesn't work for you, you can [manually find your NYT-S token](https://xwstats.com/link) and save it in your config file.
