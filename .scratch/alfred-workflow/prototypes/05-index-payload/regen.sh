#!/bin/bash
# PROTOTYPE - throwaway. Rebuilds the ticket 05 probe payloads and .alfredworkflow.
# Uses only the system Python. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"
PY=/usr/bin/python3

mkdir -p workflow
rm -f workflow/payload-*.json AardvarkPayloadProbe.alfredworkflow

for n in 1000 5000 15000 25000; do
	for form in fat lean; do
		flag=""
		[ "$form" = "lean" ] && flag="--lean"
		"$PY" generate.py --count "$n" --as alfred --no-cache $flag \
			> "workflow/payload-$n-$form.json"
	done
done
# ONE CACHED PAIR AT THE PLAUSIBLE CEILING, FOR THE WARM-PATH TEST
"$PY" generate.py --count 5000 --as alfred        > workflow/payload-5000-fat-cached.json
"$PY" generate.py --count 5000 --as alfred --lean > workflow/payload-5000-lean-cached.json

( cd workflow && zip -q -r -X ../AardvarkPayloadProbe.alfredworkflow . -x '.*' )
echo "built:"
ls -la workflow/payload-*.json AardvarkPayloadProbe.alfredworkflow
