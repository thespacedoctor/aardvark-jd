#!/bin/bash
# PROTOTYPE - TICKET 14. THROWAWAY PROBE WORKFLOW.
# LOGS EVERY INVOCATION SO A SYMLINKED LOAD CAN BE PROVEN FROM OUTSIDE
# ALFRED, THEN RETURNS ONE SCRIPT FILTER ROW.
{
  printf 'RUN %s\n' "$(date +%H:%M:%S)"
  printf '  PWD=%s\n' "$PWD"
  printf '  SCRIPT=%s\n' "$0"
  printf '  REALDIR=%s\n' "$(cd "$(dirname "$0")" && pwd -P)"
  printf '  probe_var=%s\n' "${probe_var:-<unset>}"
  printf '  alfred_workflow_bundleid=%s\n' "${alfred_workflow_bundleid:-<unset>}"
  printf '  alfred_workflow_data=%s\n' "${alfred_workflow_data:-<unset>}"
} >> "/Users/dave/git_repos/_packages_/python/aardvark-jd/.scratch/alfred-workflow/prototypes/14-alfred-write-behaviour/probe-runs.log"
cat <<'JSON'
{"items":[{"title":"ticket 14 probe ran","subtitle":"see probe-runs.log","arg":"x","valid":true}]}
JSON
