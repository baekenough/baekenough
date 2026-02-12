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

echo -e "${GREEN}[1/8] Running insights extraction...${NC}"
if [ "$DRY_RUN" = true ]; then
    python3 "$SCRIPT_DIR/update-insights.py" --dry-run
    echo -e "${YELLOW}Dry run complete. Skipping git operations.${NC}"
    exit 0
else
    python3 "$SCRIPT_DIR/update-insights.py"
fi

echo -e "${GREEN}[2/8] Changing to repository directory...${NC}"
cd "$REPO_DIR"

echo -e "${GREEN}[3/8] Checking for changes...${NC}"
# Check if there are any changes in the relevant files
if git diff --quiet README.md README_en.md insights/ 2>/dev/null; then
    echo -e "${YELLOW}No changes to commit${NC}"
    exit 0
fi

echo -e "${GREEN}[4/8] Changes detected in README or insights/${NC}"
git status --short README.md README_en.md insights/

echo -e "${GREEN}[5/8] Staging files...${NC}"
git add README.md README_en.md insights/

echo -e "${GREEN}[6/8] Creating commit...${NC}"
git commit -m "chore: update AI workflow insights"

echo -e "${GREEN}[7/8] Pushing to remote...${NC}"
git push

echo -e "${GREEN}[8/8] Deployment complete!${NC}"
echo -e "${GREEN}✓ Insights extracted and deployed successfully${NC}"
