#!/usr/bin/env python
# encoding: utf-8
"""
Documentation for aardvark can be found here: http://aardvark-jd.readthedocs.org

Usage:
    aardvark init <systemName> <parentPath> [-s <pathToSettingsFile>]
    aardvark add_area <domainLetter> <title> <description> [-e <emoji>] [-s <pathToSettingsFile>]
    aardvark add_category <area> <title> <description> [-e <emoji>] [-s <pathToSettingsFile>]
    aardvark add_id <category> <title> <description> [-s <pathToSettingsFile>]
    aardvark add_project <category> <projectTitle> [-t <templateName>] [-s <pathToSettingsFile>]
    aardvark archive <ref> [-y] [-s <pathToSettingsFile>]
    aardvark search [<term>...] [-s <pathToSettingsFile>]
    aardvark open [<path>] [-s <pathToSettingsFile>]
    aardvark set_emoji <ref> <emoji> [-s <pathToSettingsFile>]
    aardvark repair_emoji [-s <pathToSettingsFile>]
    aardvark completion <shell>
    aardvark connect_craft <apiUrl> <apiToken> [-s <pathToSettingsFile>]
    aardvark craft_sync [-s <pathToSettingsFile>]
    aardvark connect_todoist <apiToken> [-s <pathToSettingsFile>]
    aardvark todoist_sync [-s <pathToSettingsFile>]
    aardvark connect_dropbox <appKey> <appSecret> [-s <pathToSettingsFile>]
    aardvark connect_gdrive <clientId> <clientSecret> [-s <pathToSettingsFile>]
    aardvark gdrive_sync [-s <pathToSettingsFile>]

Commands:
    init                                   create a new PARA + Johnny Decimal root and index
    add_area                               add a new Johnny Decimal area to `areas`, `resources` or `projects`
    add_category                           add a new Johnny Decimal category to an existing area
    add_id                                 add a new Johnny Decimal ID to an existing category
    add_project                            create a new project (a Johnny Decimal ID) in an existing project category, from a template or blank
    archive                                retire an area, category or ID to the nearest archive folder, freeing its number
    search                                 browse the index as a tree, or search it by Johnny Decimal ref, keyword or phrase
    open                                   open the mirrored entities for a path, or pick one interactively
    set_emoji                              change the emoji on an existing folder, moving it and repointing the index
    repair_emoji                           fix drifted folder names/emoji and backfill missing reserved scaffolding
    completion                             print the shell completion script for `bash` or `zsh`
    connect_craft                          connect a craft.do space and run the initial full mirror
    craft_sync                             re-run the craft.do mirror on demand, to backfill or repair drift
    connect_todoist                        connect a Todoist account and run the initial full mirror
    todoist_sync                           re-run the Todoist mirror on demand, to backfill or repair drift
    connect_dropbox                        connect a Dropbox app and start adding Dropbox share links to synced documents
    connect_gdrive                         connect a Google Drive account and run the initial folder mirror
    gdrive_sync                            re-run the Google Drive folder mirror on demand, to backfill or repair drift

Arguments:
    systemName                             the name of the new system, e.g. "My Life"
    parentPath                             the path in which the system's root folder is created
    domainLetter                           "A" (areas), "R" (resources) or "P" (projects)
    area                                   a domain-prefixed area reference, e.g. "A10" or "A10-19"
    category                               a domain-prefixed category reference, e.g. "A11" or "P11"
    ref                                    what to target: an area ("A10-19"), category ("A11"), ID ("A11.10"), or system folder key ("root.areas")
    templateName                           a category's `04_templates` zip's basename, or "blank"
    projectTitle                           the new project's title
    emoji                                  an emoji character
    title                                  a title
    description                            a description
    term                                   a Johnny Decimal reference, or a search word or phrase
    path                                   a filesystem path to resolve to its mirrored entities (default: pick one interactively)
    shell                                  "bash" or "zsh"
    apiUrl                                 a craft.do API connection's unique base URL
    apiToken                               a craft.do or Todoist API connection token
    appKey                                 a Dropbox app's key, from the App Console
    appSecret                              a Dropbox app's secret, from the App Console
    clientId                               a Google Cloud OAuth "Desktop app" client ID
    clientSecret                           a Google Cloud OAuth "Desktop app" client secret

Options:
    -h, --help                             show the everyday commands
    --help-all                             show every command, including setup and maintenance
    -v, --version                          show version
    -e, --emoji <emoji>                    the emoji to use, skipping the suggestion and prompt
    -t, --template <templateName>          the template to use, skipping the interactive picker
    -y, --yes                              skip the confirmation prompt
    -s, --settings <pathToSettingsFile>    the settings file
"""

import os
import sys

from fundamentals import tools, times

from aardvark_jd import codes, completion, db, dropbox_ignore, folders, help_text, paths, settings_writer
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.archive import archive
from aardvark_jd.browse import browse
from aardvark_jd.connect_dropbox import connect_dropbox
from aardvark_jd.connect_gdrive import connect_gdrive
from aardvark_jd.connect_todoist import connect_todoist
from aardvark_jd.craft_sync import craft_sync
from aardvark_jd.gdrive_sync import gdrive_sync
from aardvark_jd.initialiser import initialiser
from aardvark_jd.add_project import add_project
from aardvark_jd.open_craft import open_craft
from aardvark_jd.repair_emoji import repair_emoji
from aardvark_jd.search import search, format_result, tree
from aardvark_jd.set_emoji import set_emoji
from aardvark_jd.todoist_sync import todoist_sync

CLEAR_ERRORS = (
    ValueError,
    KeyError,
    folders.DomainExhaustedError,
    folders.CategoryExhaustedError,
    folders.IdExhaustedError,
)


def main(arguments=None):
    """
    *The main function used when `cl_utils.py` is run as a single script from the cl, or when installed as a cl command*
    """
    # THE COMPLETION HELPER AND THE HELP SCREENS ARE HANDLED BEFORE
    # `fundamentals.tools` RUNS. `__complete` IS NOT DECLARED IN THE docopt
    # USAGE BLOCK AT ALL (docopt WOULD REJECT IT), AND EVEN IF IT WERE, A
    # TAB-COMPLETION MUST NOT PAY FOR SETTINGS-FILE CREATION, LOGGING SETUP
    # OR A SCHEMA MIGRATION - IT HAS TO BE FAST AND STRICTLY READ-ONLY.
    if arguments is None:
        argv = sys.argv[1:]
        if argv[:1] == [completion.COMPLETION_COMMAND]:
            completion.emit(argv[1:])
            return
        if argv[:1] == ["completion"]:
            print(completion.script(argv[1] if len(argv) > 1 else ""))
            return
        if "--help-all" in argv:
            print(help_text.full_help(__doc__))
            return
        if not argv or argv[0] in ("-h", "--help"):
            print(help_text.short_help(__doc__))
            return

    # `fundamentals.tools` copies its default settings file into
    # ~/.config/aardvark/ on first run but never creates that directory
    # first, so pre-create it here to avoid a FileNotFoundError.
    os.makedirs(os.path.expanduser("~/.config/aardvark"), exist_ok=True)

    su = tools(
        arguments=arguments,
        docString=__doc__,
        logLevel="WARNING",
        options_first=False,
        projectName="aardvark",
        distributionName="aardvark-jd",
        defaultSettingsFile=True,
    )
    arguments, settings, log, dbConn = su.setup()

    a = {}
    for arg, val in list(arguments.items()):
        if arg[0] == "-":
            varname = arg.replace("-", "") + "Flag"
        else:
            varname = arg.replace("<", "").replace(">", "")
        a[varname] = val
        log.debug("%s = %s" % (varname, val))

    startTime = times.get_now_sql_datetime()
    log.info("--- STARTING TO RUN THE cl_utils.py AT %s" % (startTime,))

    try:
        if a["init"]:
            pathToSettingsFile = arguments.get("settingsFile") or arguments.get("--settings")
            rootPath = initialiser(
                log=log, systemName=a["systemName"], parentPath=a["parentPath"],
                pathToSettingsFile=pathToSettingsFile,
            ).get()
            print(f"aardvark system '{a['systemName']}' initialised at {rootPath}")

        else:
            rootPath = (settings.get("system") or {}).get("root_path")
            if not rootPath:
                print("no aardvark system found - run `aardvark init <systemName> <parentPath>` first", file=sys.stderr)
                sys.exit(1)

            # RE-ASSERT THE DROPBOX IGNORE ON THE INDEX DIRECTORY BEFORE OPENING
            # THE DATABASE, SO A MACHINE THAT CLONED THE TREE EXCLUDES THE INDEX
            # (AND ANY `-wal`/`-shm` SIDECAR) ON ITS FIRST COMMAND. SELF-HEALING,
            # IDEMPOTENT, NEVER FATAL.
            dropbox_ignore.assert_index_ignored(rootPath, log)

            indexDbConn = db.get_connection(paths.find_db_path(rootPath))
            db.initialise_schema(indexDbConn)
            try:
                if a["connect_craft"]:
                    pathToSettingsFile = arguments.get("--settings") or su.configSettingsPath
                    settings.setdefault("craft", {})
                    settings["craft"]["enabled"] = True
                    settings["craft"]["api_url"] = a["apiUrl"]
                    settings["craft"]["api_token"] = a["apiToken"]
                    settings_writer.write_settings(pathToSettingsFile, settings)
                    _maybe_sync_gdrive(log, indexDbConn, settings)
                    _maybe_sync_todoist(log, indexDbConn, settings)
                    summary = craft_sync(log=log, dbConn=indexDbConn, settings=settings).get()
                    print(
                        f"craft connected - folders created: {summary['folders_created']}, "
                        f"documents created: {summary['documents_created']}, "
                        f"indexes refreshed: {summary['indexes_refreshed']}, "
                        f"link rows written: {summary['link_rows_written']}"
                    )
                elif a["craft_sync"]:
                    _maybe_sync_gdrive(log, indexDbConn, settings)
                    _maybe_sync_todoist(log, indexDbConn, settings)
                    summary = craft_sync(log=log, dbConn=indexDbConn, settings=settings).get()
                    print(
                        f"craft synced - folders created: {summary['folders_created']}, "
                        f"documents created: {summary['documents_created']}, "
                        f"indexes refreshed: {summary['indexes_refreshed']}, "
                        f"link rows written: {summary['link_rows_written']}"
                    )
                elif a["connect_dropbox"]:
                    pathToSettingsFile = arguments.get("--settings") or su.configSettingsPath
                    connect_dropbox(
                        log=log, appKey=a["appKey"], appSecret=a["appSecret"],
                        pathToSettingsFile=pathToSettingsFile,
                    ).get()
                    settings = settings_writer.read_settings(pathToSettingsFile)
                    _maybe_sync_gdrive(log, indexDbConn, settings)
                    _maybe_sync_todoist(log, indexDbConn, settings)
                    summary = craft_sync(log=log, dbConn=indexDbConn, settings=settings).get()
                    print(
                        f"dropbox connected - link rows written: {summary['link_rows_written']}"
                    )
                elif a["connect_gdrive"]:
                    pathToSettingsFile = arguments.get("--settings") or su.configSettingsPath
                    connect_gdrive(
                        log=log, clientId=a["clientId"], clientSecret=a["clientSecret"],
                        pathToSettingsFile=pathToSettingsFile,
                    ).get()
                    settings = settings_writer.read_settings(pathToSettingsFile)
                    summary = gdrive_sync(log=log, dbConn=indexDbConn, settings=settings).get()
                    print(
                        f"google drive connected - folders created: {summary['folders_created']}, "
                        f"link rows written: {summary['link_rows_written']}"
                    )
                    _maybe_sync_todoist(log, indexDbConn, settings)
                    _maybe_sync_craft(log, indexDbConn, settings)
                elif a["gdrive_sync"]:
                    summary = gdrive_sync(log=log, dbConn=indexDbConn, settings=settings).get()
                    print(
                        f"google drive synced - folders created: {summary['folders_created']}, "
                        f"link rows written: {summary['link_rows_written']}"
                    )
                    _maybe_sync_todoist(log, indexDbConn, settings)
                    _maybe_sync_craft(log, indexDbConn, settings)
                elif a["connect_todoist"]:
                    pathToSettingsFile = arguments.get("--settings") or su.configSettingsPath
                    connect_todoist(
                        log=log, apiToken=a["apiToken"], pathToSettingsFile=pathToSettingsFile,
                    ).get()
                    settings = settings_writer.read_settings(pathToSettingsFile)
                    summary = todoist_sync(log=log, dbConn=indexDbConn, settings=settings).get()
                    print(
                        f"todoist connected - projects created: {summary['projects_created']}, "
                        f"descriptions updated: {summary['descriptions_updated']}"
                    )
                    _maybe_sync_craft(log, indexDbConn, settings)
                elif a["todoist_sync"]:
                    summary = todoist_sync(log=log, dbConn=indexDbConn, settings=settings).get()
                    print(
                        f"todoist synced - projects created: {summary['projects_created']}, "
                        f"descriptions updated: {summary['descriptions_updated']}"
                    )
                    _maybe_sync_craft(log, indexDbConn, settings)
                else:
                    _dispatch(a, log, indexDbConn, settings)
            finally:
                indexDbConn.close()

    except CLEAR_ERRORS as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)

    endTime = times.get_now_sql_datetime()
    runningTime = times.calculate_time_difference(startTime, endTime)
    log.info(
        "-- FINISHED ATTEMPT TO RUN THE cl_utils.py AT %s (RUNTIME: %s) --"
        % (endTime, runningTime,)
    )

    return


def _maybe_sync_gdrive(log, indexDbConn, settings):
    """
    *push a Google Drive sync after a mutating command, when Drive is connected*

    Must run **first** of the three at every call site. Both the Todoist
    project description and the Craft link row now carry the entity's
    Google Drive URL (see `doc_links.todoist_description_markdown` and
    `doc_links.link_row_markdown`), so the Drive folder has to exist, and
    its link row be written, before either of the others is built. The
    resulting order is gdrive -> todoist -> craft.

    A Drive failure here is reported as a warning rather than raised,
    matching the other two - the filesystem + SQLite mutation that
    triggered it has already succeeded and remains the source of truth.

    **Key Arguments:**

    - ``log`` -- logger
    - ``indexDbConn`` -- an open SQLite connection to the active system's index
    - ``settings`` -- the aardvark settings dict
    """
    if not (settings.get("gdrive") or {}).get("enabled"):
        return
    try:
        gdrive_sync(log=log, dbConn=indexDbConn, settings=settings).get()
    except Exception as error:
        print(f"warning: google drive sync failed: {error}", file=sys.stderr)


def _maybe_sync_todoist(log, indexDbConn, settings):
    """
    *push a Todoist sync after a mutating command, when Todoist is connected*

    Must run after `_maybe_sync_gdrive` and before `_maybe_sync_craft` at
    every call site: the Todoist description embeds the entity's Drive URL,
    and the Craft link row embeds the entity's Todoist URL (see
    `craft_sync._write_link_row`), so Todoist's own project has to exist
    before Craft's sync can link to it. A Todoist failure here is
    reported as a warning rather than raised, matching `_maybe_sync_craft`
    - the filesystem + SQLite mutation that triggered it has already
    succeeded and remains the source of truth.

    **Key Arguments:**

    - ``log`` -- logger
    - ``indexDbConn`` -- an open SQLite connection to the active system's index
    - ``settings`` -- the aardvark settings dict
    """
    if not (settings.get("todoist") or {}).get("enabled"):
        return
    try:
        todoist_sync(log=log, dbConn=indexDbConn, settings=settings).get()
    except Exception as error:
        print(f"warning: todoist sync failed: {error}", file=sys.stderr)


def _maybe_sync_craft(log, indexDbConn, settings):
    """
    *push a craft.do sync after a mutating command, when craft is connected*

    A craft.do failure here is reported as a warning rather than raised,
    since the filesystem + SQLite mutation that triggered it has already
    succeeded and remains the source of truth.

    **Key Arguments:**

    - ``log`` -- logger
    - ``indexDbConn`` -- an open SQLite connection to the active system's index
    - ``settings`` -- the aardvark settings dict
    """
    if not (settings.get("craft") or {}).get("enabled"):
        return
    try:
        craft_sync(log=log, dbConn=indexDbConn, settings=settings).get()
    except Exception as error:
        print(f"warning: craft sync failed: {error}", file=sys.stderr)


def _dispatch(a, log, indexDbConn, settings):
    """
    *dispatch to the relevant worker class for the parsed command, and print its result*

    **Key Arguments:**

    - ``a`` -- the friendly-named docopt arguments dict
    - ``log`` -- logger
    - ``indexDbConn`` -- an open SQLite connection to the active system's index
    - ``settings`` -- the aardvark settings dict
    """
    if a["add_project"]:
        code, title, folderPath, templateUsed = add_project(
            log=log, dbConn=indexDbConn, categoryRef=a["category"], templateName=a["templateFlag"],
            projectTitle=a["projectTitle"], settings=settings,
        ).get()
        print(f"{code}  {title}  {folderPath} (template: {templateUsed})")
        _maybe_sync_gdrive(log, indexDbConn, settings)
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["add_area"]:
        code, folderPath = add_area(
            log=log, dbConn=indexDbConn, domain=codes.domain_from_letter(a["domainLetter"]),
            title=a["title"], description=a["description"],
            chosenEmoji=a["emojiFlag"], settings=settings,
        ).get()
        print(f"{code}  {folderPath}")
        _maybe_sync_gdrive(log, indexDbConn, settings)
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["add_category"]:
        domain, _ = codes.split_area_ref(a["area"])
        code, folderPath = add_category(
            log=log, dbConn=indexDbConn, domain=domain, areaRef=a["area"],
            title=a["title"], description=a["description"],
            chosenEmoji=a["emojiFlag"], settings=settings,
        ).get()
        print(f"{code}  {folderPath}")
        _maybe_sync_gdrive(log, indexDbConn, settings)
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["set_emoji"]:
        label, folderPath = set_emoji(
            log=log, dbConn=indexDbConn, ref=a["ref"], newEmoji=a["emoji"],
        ).get()
        print(f"{label}  {folderPath}")
        _maybe_sync_gdrive(log, indexDbConn, settings)
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["repair_emoji"]:
        repaired = repair_emoji(log=log, dbConn=indexDbConn).get()
        if not repaired:
            print("every folder already matches the current naming convention")
        for folderKey, folderPath in repaired:
            print(f"{folderKey}  {folderPath}")
        _maybe_sync_gdrive(log, indexDbConn, settings)
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["add_id"]:
        domain, _ = codes.split_category_ref(a["category"])
        code, folderPath = add_id(
            log=log, dbConn=indexDbConn, domain=domain, categoryRef=a["category"],
            title=a["title"], description=a["description"],
        ).get()
        print(f"{code}  {folderPath}")
        _maybe_sync_gdrive(log, indexDbConn, settings)
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["search"]:
        _search(a, log, indexDbConn)

    elif a["archive"]:
        if not a["yesFlag"] and sys.stdin.isatty():
            answer = input(f"archive '{a['ref']}' and free its number? [y/N] ").strip().lower()
            if answer not in ("y", "yes"):
                print("nothing archived")
                return
        code, archivedPath, warnings = archive(
            log=log, dbConn=indexDbConn, ref=a["ref"], settings=settings,
        ).get()
        print(f"archived {code}  {archivedPath}")
        for warning in warnings:
            print(f"note: {warning}", file=sys.stderr)

    elif a["open"]:
        targetPath = a["path"]
        if not targetPath and sys.stdin.isatty():
            targetPath = browse(log=log, dbConn=indexDbConn, settings=settings).get()
            if not targetPath:
                print("nothing selected")
                return
        label, openedUrls = open_craft(
            log=log, dbConn=indexDbConn, path=targetPath, settings=settings,
        ).get()
        for serviceLabel, url in openedUrls:
            print(f"opened {label}  {serviceLabel}  {url}")


def _id_row_for_ref(indexDbConn, ref):
    """
    *the `ids` row a Johnny Decimal ID reference points at, or None if it isn't one*

    An ID reference carries a second period, before its item number
    (`A11.10`); an area or category reference never does.

    **Key Arguments:**

    - ``indexDbConn`` -- an open SQLite connection to the active system's index
    - ``ref`` -- the reference to test, already upper-cased

    **Return:**

    - ``row`` -- the `ids` row, or `None` if `ref` is not an ID reference or matches nothing
    """
    if not codes.is_id_ref(ref):
        return None
    domain, acNumber, itemNumber = codes.split_id_ref(ref)
    return db.get_id(indexDbConn, domain, acNumber, itemNumber)


def _search(a, log, indexDbConn):
    """
    *print the index as a tree, a Johnny Decimal subtree, or keyword search results*

    With no term at all the whole index is rendered as a tree. A single
    term that looks like a Johnny Decimal reference **and resolves** is
    treated as one: a domain letter, area or category prints its subtree,
    and an ID prints its path line. Anything else - including a ref-shaped
    term that matches nothing - falls through to the existing keyword
    search, so `search A` can still find the word "A" if that is genuinely
    what the user meant.

    **Key Arguments:**

    - ``a`` -- the friendly-named docopt arguments dict
    - ``log`` -- logger
    - ``indexDbConn`` -- an open SQLite connection to the active system's index
    """
    terms = a["term"] or []

    if not terms:
        for line in tree(log=log, dbConn=indexDbConn).get():
            print(line)
        return

    if len(terms) == 1:
        ref = terms[0]
        try:
            if codes.is_jd_ref(ref) or codes.is_id_ref(ref) or ref.upper() in codes.LETTER_DOMAIN:
                normalised = ref.upper()
                idRow = _id_row_for_ref(indexDbConn, normalised)
                if idRow is not None:
                    print(f"{normalised}  {idRow['title']}  {idRow['folder_path']}")
                    return
                for line in tree(log=log, dbConn=indexDbConn, ref=normalised).get():
                    print(line)
                return
        except (ValueError, KeyError):
            # NOT A RESOLVABLE REF AFTER ALL - FALL THROUGH TO KEYWORD SEARCH.
            pass

    results = search(log=log, dbConn=indexDbConn, terms=terms).get()
    if not results:
        print("no matches found")
    for row in results:
        print(format_result(row))


if __name__ == "__main__":
    main()
