# What does `aardvark install_alfred` do?

Type: grilling
Status: open
Blocked by: 02, 04, 14

## Question

Settled while charting: a new CLI command deploys the workflow into Alfred and bakes in the interpreter path it is running from, because the CLI is the only thing that knows where it is installed (`sys.executable`) without guessing. This ticket decides what the command actually does.

Decide:

- **Link or copy?** A link means repo edits take effect immediately, which is the author's workflow; a copy is what a package user needs, and it is what survives the repo directory moving or disappearing. Decide whether the command does both behind a flag, or picks one and lets the other route be the exported `.alfredworkflow`.
- **What it writes, and where.** Whether it creates the `user.workflow.<UUID>` directory itself or drives Alfred's own import, and how it decides the UUID — the answer comes from ticket 02.
- **Idempotency and upgrade.** What happens when the workflow is already installed: replace, refuse, or update in place. What happens after `pip install --upgrade` when the package's workflow has moved on but the installed copy has not, and whether the workflow can detect that itself and say so in a result row.
- **What "baking in the path" means concretely.** Whether the interpreter path is written into `info.plist`, into a workflow configuration variable, or into a small generated file the scripts read — and how that interacts with ticket 04's decision about whether the plist is generated. Note that ticket 12 may constrain this heavily.
- **Uninstall.** Whether there is a matching removal path, or whether deleting the workflow in Alfred's UI is sufficient and safe given what this command wrote.
- **Where it appears in the CLI.** The usage block hides setup and maintenance commands behind `--help-all`. Decide whether `install_alfred` is an everyday command or a hidden one, and note that adding it means the workflow's own scope decision — that setup commands are out of scope for the Alfred surface — now has an exception living in the CLI.
- **What it does when Alfred is not installed.** A clear failure, not a traceback.
