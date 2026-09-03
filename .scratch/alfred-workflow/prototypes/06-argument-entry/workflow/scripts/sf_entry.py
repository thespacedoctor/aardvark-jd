#!/usr/bin/env python
"""PROTOTYPE - wayfinder ticket 06. THROWAWAY.

Step 2 of the two-step `add_id` entry flow: one free-text field that takes
`title <SEP> description`. Re-runs on every keystroke, parses the query, and
renders a live preview so the interaction can be felt.

What this prototype is probing (see probe.md):
  - does the chosen category stay visible while the title is typed?
  - what is the right separator? (SEP is a workflow variable - retype it in
    the workflow's configuration and feel each candidate)
  - what happens when the title contains the separator, or the description is
    omitted, or only a description is typed?
  - does a preview row before the commit help or just add a keystroke?

Alfred does NOT filter these results (`alfredfiltersresults` is off) - the
script owns what is shown.
"""
import json
import os
import sys

SEP = os.environ.get("SEP") or "::"
CATEGORY_CODE = os.environ.get("CATEGORY_CODE", "?")
CATEGORY_LABEL = os.environ.get("CATEGORY_LABEL", "(no category chosen)")


def parse(query):
    """Split on the FIRST separator only. Everything after it - including
    further separators - is the description."""
    if SEP in query:
        title, description = query.split(SEP, 1)
        return title.strip(), description.strip()
    return query.strip(), ""


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    title, description = parse(query)

    items = []

    if not query.strip():
        items.append(
            {
                "title": f"Add an ID to {CATEGORY_LABEL}",
                "subtitle": f"type a title, then  {SEP}  then a description",
                "valid": False,
            }
        )
    elif not title:
        items.append(
            {
                "title": "Title is empty",
                "subtitle": f"you typed only a description. Put the title before the  {SEP}",
                "valid": False,
            }
        )
    else:
        desc_display = description if description else "(no description)"
        items.append(
            {
                "title": f"Create  {CATEGORY_CODE}.NN  {title}",
                "subtitle": (
                    f"{desc_display}   ·   ↩ creates it in {CATEGORY_LABEL}"
                    "   ·   emoji (07) + spell-check (08) steps insert here"
                ),
                "arg": f"{CATEGORY_CODE} :: {title} :: {desc_display}",
                "variables": {"TITLE": title, "DESCRIPTION": description},
            }
        )

    # ALWAYS SHOW THE RAW PARSE AS A NON-ACTIONABLE ROW, SO THE SEPARATOR'S
    # BEHAVIOUR IS VISIBLE AT EVERY KEYSTROKE.
    items.append(
        {
            "title": f"parse:  title = «{title}»    description = «{description}»",
            "subtitle": f"separator = {SEP!r}    category = {CATEGORY_CODE}    (this row does nothing)",
            "valid": False,
        }
    )

    json.dump({"items": items}, sys.stdout)


if __name__ == "__main__":
    main()
