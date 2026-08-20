#!/usr/bin/env python
# encoding: utf-8
"""
Documentation for aardvark can be found here: http://aardvark-jd.readthedocs.org

Usage:
    aardvark init <systemName> <parentPath> [-s <pathToSettingsFile>]
    aardvark new_project <category> <projectTitle> [-t <templateName>] [-s <pathToSettingsFile>]
    aardvark add_area <domainLetter> <title> <description> [-e <emoji>] [-s <pathToSettingsFile>]
    aardvark add_category <area> <title> <description> [-e <emoji>] [-s <pathToSettingsFile>]
    aardvark add_id <category> <title> <description> [-s <pathToSettingsFile>]
    aardvark set_emoji <ref> <emoji> [-s <pathToSettingsFile>]
    aardvark repair_emoji [-s <pathToSettingsFile>]
    aardvark search <term>... [-s <pathToSettingsFile>]
    aardvark connect_craft <apiUrl> <apiToken> [-s <pathToSettingsFile>]
    aardvark craft_sync [-s <pathToSettingsFile>]
    aardvark connect_dropbox <appKey> <appSecret> [-s <pathToSettingsFile>]
    aardvark connect_todoist <apiToken> [-s <pathToSettingsFile>]
    aardvark todoist_sync [-s <pathToSettingsFile>]
    aardvark open [<path>] [-s <pathToSettingsFile>]

Commands:
    init                                   create a new PARA + Johnny Decimal root and index
    new_project                            create a new project (a Johnny Decimal ID) in an existing project category, from a template or blank
    add_area                               add a new Johnny Decimal area to `areas`, `resources` or `projects`
    add_category                           add a new Johnny Decimal category to an existing area
    add_id                                 add a new Johnny Decimal ID to an existing category
    set_emoji                              change the emoji on an existing folder, moving it and repointing the index
    repair_emoji                           fix drifted folder names/emoji and backfill missing reserved scaffolding
    search                                 search the index by keyword or phrase
    connect_craft                          connect a craft.do space and run the initial full mirror
    craft_sync                             re-run the craft.do mirror on demand, to backfill or repair drift
    connect_dropbox                        connect a Dropbox app and start adding Dropbox share links to synced documents
    connect_todoist                        connect a Todoist account and run the initial full mirror
    todoist_sync                           re-run the Todoist mirror on demand, to backfill or repair drift
    open                                   open the Craft/Todoist entities that mirror a filesystem path (default: the current directory)

Arguments:
    systemName                             the name of the new system, e.g. "My Life"
    parentPath                             the path in which the system's root folder is created
    templateName                           a category's `04_templates` zip's basename, or "blank"
    projectTitle                           the new project's title
    domainLetter                           "A" (areas), "R" (resources) or "P" (projects)
    area                                   a domain-prefixed area reference, e.g. "A10" or "A10-19"
    category                               a domain-prefixed category reference, e.g. "A11" or "P11"
    ref                                    what to retarget: an area ("A10-19"), category ("A11"), or system folder key ("root.areas")
    emoji                                  an emoji character
    title                                  a title
    description                            a description
    term                                   a search word or phrase
    apiUrl                                 a craft.do API connection's unique base URL
    apiToken                               a craft.do or Todoist API connection token
    appKey                                 a Dropbox app's key, from the App Console
    appSecret                              a Dropbox app's secret, from the App Console
    path                                   a filesystem path to resolve to its Craft/Todoist entities (default: the current directory)

Options:
    -h, --help                             show this help message
    -v, --version                          show version
    -e, --emoji <emoji>                    the emoji to use, skipping the suggestion and prompt
    -t, --template <templateName>          the template to use, skipping the interactive picker
    -s, --settings <pathToSettingsFile>    the settings file
"""

import os
import sys

from fundamentals import tools, times

from aardvark_jd import codes, db, folders, paths, settings_writer
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.connect_dropbox import connect_dropbox
from aardvark_jd.connect_todoist import connect_todoist
from aardvark_jd.craft_sync import craft_sync
from aardvark_jd.initialiser import initialiser
from aardvark_jd.new_project import new_project
from aardvark_jd.open_craft import open_craft
from aardvark_jd.repair_emoji import repair_emoji
from aardvark_jd.search import search, format_result
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
                    _maybe_sync_todoist(log, indexDbConn, settings)
                    summary = craft_sync(log=log, dbConn=indexDbConn, settings=settings).get()
                    print(
                        f"craft connected - folders created: {summary['folders_created']}, "
                        f"documents created: {summary['documents_created']}, "
                        f"indexes refreshed: {summary['indexes_refreshed']}, "
                        f"link rows written: {summary['link_rows_written']}"
                    )
                elif a["craft_sync"]:
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
                    _maybe_sync_todoist(log, indexDbConn, settings)
                    summary = craft_sync(log=log, dbConn=indexDbConn, settings=settings).get()
                    print(
                        f"dropbox connected - link rows written: {summary['link_rows_written']}"
                    )
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


def _maybe_sync_todoist(log, indexDbConn, settings):
    """
    *push a Todoist sync after a mutating command, when Todoist is connected*

    Must run before `_maybe_sync_craft` at every call site: the Craft
    link row embeds the entity's Todoist URL (see
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
    if a["new_project"]:
        code, title, folderPath, templateUsed = new_project(
            log=log, dbConn=indexDbConn, categoryRef=a["category"], templateName=a["templateFlag"],
            projectTitle=a["projectTitle"], settings=settings,
        ).get()
        print(f"{code}  {title}  {folderPath} (template: {templateUsed})")
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["add_area"]:
        code, folderPath = add_area(
            log=log, dbConn=indexDbConn, domain=codes.domain_from_letter(a["domainLetter"]),
            title=a["title"], description=a["description"],
            chosenEmoji=a["emojiFlag"], settings=settings,
        ).get()
        print(f"{code}  {folderPath}")
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
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["set_emoji"]:
        label, folderPath = set_emoji(
            log=log, dbConn=indexDbConn, ref=a["ref"], newEmoji=a["emoji"],
        ).get()
        print(f"{label}  {folderPath}")
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["repair_emoji"]:
        repaired = repair_emoji(log=log, dbConn=indexDbConn).get()
        if not repaired:
            print("every folder already matches the current naming convention")
        for folderKey, folderPath in repaired:
            print(f"{folderKey}  {folderPath}")
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["add_id"]:
        domain, _ = codes.split_category_ref(a["category"])
        code, folderPath = add_id(
            log=log, dbConn=indexDbConn, domain=domain, categoryRef=a["category"],
            title=a["title"], description=a["description"],
        ).get()
        print(f"{code}  {folderPath}")
        _maybe_sync_todoist(log, indexDbConn, settings)
        _maybe_sync_craft(log, indexDbConn, settings)

    elif a["search"]:
        results = search(log=log, dbConn=indexDbConn, terms=a["term"]).get()
        if not results:
            print("no matches found")
        for row in results:
            print(format_result(row))

    elif a["open"]:
        label, craftUrl, todoistUrl = open_craft(log=log, dbConn=indexDbConn, path=a["path"], settings=settings).get()
        if craftUrl:
            print(f"opened {label}  {craftUrl}")
        if todoistUrl:
            print(f"opened {label}  {todoistUrl}")


if __name__ == "__main__":
    main()
