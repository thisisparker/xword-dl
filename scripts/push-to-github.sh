#!/bin/bash
# Quick setup script to push xword-dl fork to GitHub

set -e

echo "==============================================================="
echo "Seattle Times Midi - xword-dl Fork Setup"
echo "==============================================================="
echo ""
echo "This will push your xword-dl fork to GitHub: slmingol/xword-dl"
echo ""

# Go to xword-dl directory
cd ~/dev/projects/xword-dl

echo "Current branch:"
git branch | grep '*'
echo ""

# Check if we're on the right branch
if ! git branch | grep -q '* feature/seattle-times-midi'; then
    echo "ERROR: Not on feature/seattle-times-midi branch"
    echo "Run: git checkout feature/seattle-times-midi"
    exit 1
fi

echo "Step 1: Check if GitHub fork exists"
echo "-----------------------------------"
echo "Testing connection to github.com/slmingol/xword-dl..."
echo ""

if git ls-remote slmingol &>/dev/null; then
    echo "✓ Fork exists at github.com/slmingol/xword-dl"
else
    echo "✗ Fork doesn't exist yet"
    echo ""
    echo "Please create the fork first:"
    echo "1. Go to: https://github.com/thisisparker/xword-dl"
    echo "2. Click 'Fork' button (top right)"
    echo "3. Create fork under 'slmingol' account"
    echo ""
    read -p "Press ENTER once you've created the fork..."
    echo ""
fi

echo "Step 2: Push feature branch"
echo "---------------------------"
git push slmingol feature/seattle-times-midi

echo ""
echo "==============================================================="
echo "SUCCESS!"
echo "==============================================================="
echo ""
echo "Your fork is now available at:"
echo "  https://github.com/slmingol/xword-dl/tree/feature/seattle-times-midi"
echo ""
echo "Next steps:"
echo ""
echo "1. Build scraper with your fork:"
echo "   cd ~/dev/projects/crossword-catastrophe"
echo "   docker-compose build scraper"
echo ""
echo "2. The Dockerfile installs from your GitHub fork:"
echo "   git+https://github.com/slmingol/xword-dl.git@feature/seattle-times-midi"
echo ""
echo "3. Deploy:"
echo "   docker-compose up -d"
echo ""
echo "4. [Optional] Create PR to upstream xword-dl:"
echo "   https://github.com/thisisparker/xword-dl/compare/main...slmingol:xword-dl:feature/seattle-times-midi"
echo ""
