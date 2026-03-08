#!/usr/bin/env bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script and repo directories
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Parse arguments
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

echo -e "${GREEN}[1/12] Running insights extraction...${NC}"
if [ "$DRY_RUN" = true ]; then
    python3 "$SCRIPT_DIR/update-insights.py" --dry-run
    echo -e "${YELLOW}Dry run complete. Skipping git operations.${NC}"
    exit 0
else
    python3 "$SCRIPT_DIR/update-insights.py"
fi

echo -e "${GREEN}[2/12] Changing to repository directory...${NC}"
cd "$REPO_DIR"

echo -e "${GREEN}[3/12] Checking for changes...${NC}"
# Check if there are any changes (tracked modifications + untracked files)
CHANGES=$(git status --porcelain README.md README_en.md insights/ scripts/ 2>/dev/null)
if [ -z "$CHANGES" ]; then
    echo -e "${YELLOW}No changes to commit${NC}"
    exit 0
fi

echo -e "${GREEN}[4/12] Changes detected in README or insights/${NC}"
git status --short README.md README_en.md insights/ scripts/

echo -e "${GREEN}[5/12] Staging files...${NC}"
git add README.md README_en.md insights/ scripts/

echo -e "${GREEN}[6/12] Creating commit...${NC}"
git commit -m "chore: update AI workflow insights"

echo -e "${GREEN}[7/12] Pushing to remote...${NC}"
git push

# OMAS Agentic Score - scan and upload to leaderboard
echo -e "${GREEN}[8/12] Scanning baekenough agentic score...${NC}"
omas --claude-dir ~/workspace/claude/baekenough scan

echo -e "${GREEN}[9/12] Scanning baekgomiyo agentic score...${NC}"
omas --claude-dir ~/workspace/claude/baekgomiyo scan

echo -e "${GREEN}[10/12] Scanning current directory agentic score...${NC}"
omas scan

echo -e "${GREEN}[11/12] Uploading scores to leaderboard...${NC}"
omas upload

echo -e "${GREEN}[12/12] Deployment complete!${NC}"
echo -e "${GREEN}✓ Insights extracted and deployed successfully${NC}"
