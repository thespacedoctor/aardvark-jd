#!/bin/bash
# PROTOTYPE - wayfinder ticket 06. THROWAWAY.
# Zips workflow/ into an importable .alfredworkflow. Run ./setup.sh first.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f workflow/scripts/env.sh ]; then
	echo "error: workflow/scripts/env.sh is missing - run ./setup.sh first." >&2
	exit 1
fi

chmod +x workflow/scripts/*.sh workflow/scripts/*.py
find workflow -name __pycache__ -type d -exec rm -rf {} +
rm -f AardvarkArgEntryProbe.alfredworkflow

( cd workflow && zip -q -r -X ../AardvarkArgEntryProbe.alfredworkflow . -x '.*' )

echo "built: $(pwd)/AardvarkArgEntryProbe.alfredworkflow"
echo "import it: open AardvarkArgEntryProbe.alfredworkflow"
