# xword-dl fork with Seattle Times Midi Support

This is a fork of [thisisparker/xword-dl](https://github.com/thisisparker/xword-dl) with added support for Seattle Times Midi crossword puzzles.

## What's Added

### Seattle Times Midi Downloader

Command: `stm`

Downloads Seattle Times Midi crossword puzzles - smaller crosswords (9×9 to 11×11) with 30-44 clues, perfect for mobile devices.

**Features:**
- Latest puzzle: `xword-dl stm --latest`
- Date-based: `xword-dl stm --date "May 1, 2026"`
- Grid sizes: 9×9, 10×10, 11×11
- Significantly fewer clues than standard 15×15 puzzles (30-44 vs 70-80)

**Implementation:**
- File: `src/xword_dl/downloader/seattletimesdownloader.py`
- Base class: `AmuseLabsDownloader` (same as LA Times, Newsday)
- Platform: AmuseLabs PuzzleMe
- Puzzle set: `seattletimes-crossword-midi`

### Branch Information

- **Branch:** `feature/seattle-times-midi`
- **Status:** Working and tested
- **Integration:** Used by [slmingol/crossword-catastrophe](https://github.com/slmingol/crossword-catastrophe)

## Installation

### From this fork

```bash
pip install git+https://github.com/slmingol/xword-dl.git@feature/seattle-times-midi
```

### Local development

```bash
git clone https://github.com/slmingol/xword-dl.git
cd xword-dl
git checkout feature/seattle-times-midi
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage Examples

```bash
# Download latest Seattle Times Midi puzzle
xword-dl stm --latest

# Download puzzle from specific date
xword-dl stm --date "yesterday"
xword-dl stm --date "May 1, 2026"

# Custom output filename
xword-dl stm --latest -o ~/puzzles/seattle-midi-today.puz
```

## Testing

```bash
# Test latest download
xword-dl stm --latest -o /tmp/test.puz

# Verify puzzle
python3 -c "
import puz
p = puz.read('/tmp/test.puz')
print(f'Title: {p.title}')
print(f'Author: {p.author}')
print(f'Size: {p.width}×{p.height}')
print(f'Clues: {len(p.clues)}')
"
```

**Expected output:**
```
Title: [Puzzle Title]
Author: Phil Fraas
Size: 9×9 (or 10×10, 11×11)
Clues: 30-44
```

## Technical Details

### API Endpoints

- **Picker:** `https://seattletimes.amuselabs.com/puzzleme/date-picker?set=seattletimes-crossword-midi`
- **Crossword:** `https://seattletimes.amuselabs.com/puzzleme/crossword?id={puzzle_id}&set=seattletimes-crossword-midi`

### Puzzle ID Format

- Sequential IDs: `midi-crossword-111`, `midi-crossword-110`, etc.
- Not date-based (requires lookup via picker API)

### Date Lookup

Since puzzles use sequential IDs rather than date-based IDs, the downloader:
1. Fetches the picker page
2. Parses puzzle metadata JSON
3. Matches requested date to publication timestamp
4. Extracts puzzle ID
5. Downloads puzzle

### Archive Depth

Limited to ~14 days of recent puzzles based on observed data.

## Integration with crossword-catastrophe

This fork is used by the [crossword-catastrophe](https://github.com/slmingol/crossword-catastrophe) project scraper:

```dockerfile
# packages/scraper/Dockerfile
RUN pip install --no-cache-dir git+https://github.com/slmingol/xword-dl.git@feature/seattle-times-midi
```

The scraper automatically downloads puzzles from multiple sources including Seattle Times Midi.

## Contributing Back to Upstream

This feature can be contributed back to the main xword-dl project:

1. Ensure tests pass
2. Create PR: https://github.com/thisisparker/xword-dl/compare/main...slmingol:feature/seattle-times-midi
3. Include documentation and test results

### Why This Might Be Accepted Upstream

- Uses existing `AmuseLabsDownloader` infrastructure
- Follows established patterns (similar to LA Times, Newsday)
- Minimal code addition (~70 lines)
- Provides value: smaller puzzles for mobile users
- Fully tested and working

## Changes from Upstream

Only additions, no modifications to existing code:

```
new file:   src/xword_dl/downloader/seattletimesdownloader.py
```

The downloader is automatically discovered via `get_plugins()` in `downloader/__init__.py`.

## Maintenance

To update this fork with upstream changes:

```bash
cd xword-dl
git remote add upstream https://github.com/thisisparker/xword-dl.git
git fetch upstream
git checkout feature/seattle-times-midi
git rebase upstream/main
git push slmingol feature/seattle-times-midi --force-with-lease
```

## License

Same as upstream: MIT License

## Credits

- Original xword-dl: [Parker Higgins](https://github.com/thisisparker)
- Seattle Times Midi support: Added for [crossword-catastrophe](https://github.com/slmingol/crossword-catastrophe) project
- Inspiration: LA Times and Newsday downloaders
