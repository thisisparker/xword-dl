# xword-dl

`xword-dl` is a command-line tool to download .puz files for online crossword puzzles. For a supported outlet, you can easily download the latest puzzle, or specify one from the archives.

Currently, `xword-dl` supports:
* The New Yorker
* Newsday
* The LA Times
* The Wall Street Journal
* The Washington Post
* USA Today

To download a puzzle, run `xword-dl` on the command line. For example, to download the latest New Yorker puzzle, you could run:

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

The resulting .puz file can be opened with `[cursewords](https://github.com/thisisparker/cursewords)` or any other puz file reader.
