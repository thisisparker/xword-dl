# Seattle Times Midi Crossword Support

This branch adds support for downloading Seattle Times Midi crossword puzzles.

## Status: URL Discovery Needed

The implementation is complete structurally, but the actual API endpoint URLs need to be verified via browser inspection.

## How to Complete the Implementation

### Step 1: Discover the API URLs

1. Open https://www.seattletimes.com/games-crossword-midi/ in Chrome/Firefox
2. Open Developer Tools (F12)
3. Go to the **Network** tab
4. Clear the network log
5. Reload the page and let the puzzle load
6. Look for requests to `amuselabs.com` domains
7. Find requests containing:
   - `date-picker` - this is the picker URL
   - `crossword` with query params - this is the puzzle URL
8. Note the exact URL patterns

### Step 2: Update the Code

Edit `src/xword_dl/downloader/seattletimesdownloader.py`:

```python
# Update these URLs with the discovered patterns:
self.picker_url = "https://DISCOVERED_URL/date-picker?set=seattletimes-crossword-midi"
self.url_from_id = "https://DISCOVERED_URL/crossword?id={puzzle_id}&set=seattletimes-crossword-midi"

# Update puzzle ID format based on what you see in the network traffic:
self.id = f"DISCOVERED_FORMAT-{url_formatted_date}"
```

### Step 3: Test

```bash
# Install from this branch
uv tool install --force git+https://github.com/YOUR_USERNAME/xword-dl.git@feature/seattle-times-midi

# Test latest puzzle
xword-dl stm --latest

# Test specific date
xword-dl stm --date 5/1/26
```

## Technical Details

### Infrastructure
- Platform: AmuseLabs PuzzleMe (same as LA Times, Newsday)
- Puzzle Set: `seattletimes-crossword-midi`
- Base Domain: `seattletimes.amuselabs.com` (confirmed from page source)

### Implementation
- Extends: `AmuseLabsDownloader` base class
- Command: `stm`
- Pattern: Similar to `LATimesDownloader` and `NewsdayDownloader`

### Why URLs Are Unknown

The Seattle Times website blocks direct API access (returns 403 Forbidden or 404 Not Found for automated requests). The puzzle loads via JavaScript in the browser, which makes the actual API calls. We need to observe those calls in a real browser to get the correct URL patterns.

Common patterns attempted (all returned 404):
- `https://seattletimes.amuselabs.com/st/date-picker`
- `https://cdn3.amuselabs.com/st/date-picker`
- `https://seattletimes.amuselabs.com/puzzles/date-picker`

## Once Working

This will enable downloading:
- Seattle Times Midi crosswords (12x12 or 13x13 grids)
- Smaller puzzles suitable for mobile devices
- Historical puzzle archive
- Daily automated scraping

## Contributing Back to Upstream

Once the URLs are discovered and tested:
1. Commit the working changes
2. Add tests (if upstream requires them)
3. Submit PR to https://github.com/thisisparker/xword-dl
