# Assemble the build specification

Type: grilling
Status: open
Blocked by: 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 14, 15

## Question

The last ticket on the map. Every decision above is made; this one turns them into the single document a TDD implementation session can be handed.

Produce a spec covering:

- **The command inventory.** Each of the fifteen in-scope commands mapped to its concrete Alfred surface: what the user types, what Alfred shows, what modifiers do, what is invoked, and what is reported back. Any command that turned out not to earn a surface is listed with the reason.
- **The CLI changes.** The `--json` contract from ticket 03 and the `install_alfred` command from ticket 10, written as behaviour to test rather than as code.
- **The workflow's file layout.** What lives in the repo directory, in what form, per ticket 04, and which parts are generated.
- **The module layout inside the package.** Where the testable logic sits under `aardvark_jd/alfred/`, what the Alfred-invoked entry points look like, and what is excluded from coverage.
- **The build order.** What has to exist before what, and which slice is a usable workflow on its own — the smallest thing worth installing, so the rest can be judged against something real.
- **The test plan.** Per the user's global rules: what is tested first, what 80 per cent coverage means for a package half of which is Alfred glue, and what is deliberately untested.
- **The documentation changes.** The README section and docs page from the charting decision, and where the internal-and-unstable status of the JSON contract is stated so a future reader does not mistake it for API.

Before writing it, re-read the map's Not-yet-specified section: some of that fog will have cleared while the tickets were resolved, and anything now sharp either belongs in the spec or belongs in a new ticket rather than being quietly forgotten.
