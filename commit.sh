#!/bin/bash
# Commit and push script for Planner Validation updates

echo "=== UPA Dev - Git Commit Script ==="
echo ""

# Stage all changes
git add -A

echo "Files to commit:"
git status --short
echo ""

# Commit with message
git commit -m "Add Planner Validation Framework

Changes:
- Merge planner.py into upa.py for single-file simplicity
- Add planner validation test suite (benchmarks/suites/planner.py)
  - 18 test cases for intent, tools, and skip_planning validation
  - Automated accuracy reporting in benchmark results
- Add framework unit tests (tests/)
  - test_planner.py: Planner module unit tests
  - test_runner.py: Benchmark utilities tests
- Fix suite registration bug (classic, mmlu now properly registered)
- Deprecate legacy benchmark files (benchmark_upa.py, benchmark_semantic.py)
- Add pytest as development dependency
- Update README.md and add CHANGELOG.md

Validation:
- uv run python -m benchmarks planner -w 4 shows accuracy metrics
- uv run pytest tests/ -v runs unit tests"

echo ""
echo "Commit created. Push to remote? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
    git push
    echo "Pushed to remote."
else
    echo "Commit ready to push manually."
fi
