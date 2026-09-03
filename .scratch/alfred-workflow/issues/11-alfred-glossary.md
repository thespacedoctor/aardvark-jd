# What are the Alfred surface's terms called?

Type: task
Status: open

## Question

`CONTEXT.md` fixes the vocabulary this codebase shares, and the Alfred surface introduces terms it does not cover. The charting grilling already turned up one collision: the action that opens a terminal at an entity's folder cannot be called `cd`, because in this system `cd` names a shell function that changes the current shell's directory, and the Alfred action does something different.

Work through the vocabulary the Alfred surface needs and add it to `CONTEXT.md`, keeping that file a glossary and nothing else — no implementation detail, no spec.

At minimum, settle:

- **What the terminal-handoff action is called**, given `cd` is taken and "reveal" implies Finder.
- **Whether Alfred's own vocabulary is adopted or translated.** "Workflow", "Script Filter", "modifier", "keyword" and "configuration variable" are Alfred's terms with precise meanings; decide whether they enter this glossary as-is, and mark them as Alfred's rather than aardvark's if so.
- **What the whole thing is called.** "The Alfred workflow" is serviceable; whether it needs a name of its own that can appear in the README, the docs and `install_alfred`'s help text.
- **A word for the JSON contract** between the CLI and the workflow, so tickets and code can refer to it without spelling it out each time.
- **Whether any existing term shifts.** "Mirror" is defined as an external service the tree is reproduced into. Alfred is not one — it drives the CLI rather than holding a copy of the tree — and the glossary should make that distinction impossible to blur, since the workflow will sit alongside four things that are mirrors.

This ticket is unblocked and can run at any point, but it will read better once at least one prototype has produced concrete surfaces to name.
