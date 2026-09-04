# What are the Alfred surface's terms called?

Type: task
Status: resolved
Assignee: Dave

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

## Resolution (2026-09-04)

Fifteen terms added to `CONTEXT.md`, in three places. All five of the ticket's minimum questions are settled, plus three more terms the prototypes made concrete.

**The terminal handoff is called a handoff.** Glossed as "opening a new terminal tab at an entity's folder", with an explicit `_Avoid_` against calling it `cd`. The word was already the natural one in ticket 09's answer, it collides with no CLI command name, and it works as both noun and verb. **Reveal** is defined beside it for the Finder action, so the three destinations — the mirrors, Finder, the terminal — each own exactly one word.

**Alfred's vocabulary is adopted verbatim, not translated.** `Workflow`, `Script Filter`, `Modifier`, `Keyword` and `Configuration variable` sit in their own `## Alfred's language` section, which states once that they are Alfred's terms carrying Alfred's meanings. Translating them would have created two names per concept, and every Alfred document the reader reaches for uses Alfred's word. The section header does the marking, so no per-term prefix is needed.

**The whole thing has no proper name.** It is *the aardvark workflow*, lowercase and descriptive, in the README, the docs and `install_alfred`'s help text alike. A codename would add a lookup step for a reader searching for "Alfred" and buy nothing for a one-user product.

**The JSON contract** names the agreed shape of `--json` output; short form, "the contract". **Index payload** is kept distinct as the narrower term for the whole index fetched in one call, so ticket 05's word is not overloaded onto ticket 03's. The contract's entry records that it is internal rather than a public API, matching the charting decision.

**Mirror shifted, and surface became a term.** `Mirror` gains an `_Avoid_` line ruling out calling a surface a mirror, and **Surface** is defined as a place the system is driven from that holds no copy of the tree — the command line and the aardvark workflow both. This makes the boundary explicit rather than implied, which matters because the workflow will be listed alongside four things that *are* mirrors. The distinction is stated in terms of what each holds: a mirror is synced to and can drift; a surface is neither.

Three further terms earned entries because ticket 13's spec will refer to each repeatedly, and each is a concept rather than an implementation detail: **confirmation screen** (ticket 06/08's pre-commit screen, where corrections arrive as rows rather than steps), **binary pointer** (ticket 12's per-machine path file, with an `_Avoid_` marking it off from Alfred's synced configuration variable), and **error row** (ticket 01/12's "errors are results, not exceptions" pattern). Nothing not yet decided was named.

Nothing was renamed in code and no implementation detail entered `CONTEXT.md`; the file stays a glossary. Unblocks [ticket 13](13-assemble-the-spec.md).
