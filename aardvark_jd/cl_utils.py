#!/usr/bin/env python
# encoding: utf-8
"""
Documentation for aardvark can be found here: http://aardvark-jd.readthedocs.org

Usage:
    aardvark init <systemName> <parentPath> [-s <pathToSettingsFile>]
    aardvark new_project [<templateName>] [<projectTitle>] [-s <pathToSettingsFile>]
    aardvark add_area <domain> <title> <description> [-s <pathToSettingsFile>]
    aardvark add_category <domain> <area> <title> <description> [-s <pathToSettingsFile>]
    aardvark add_id <domain> <category> <title> <description> [-s <pathToSettingsFile>]
    aardvark search <term>... [-s <pathToSettingsFile>]

Commands:
    init                                   create a new PARA + Johnny Decimal root and index
    new_project                            create a new project under Projects, from a template or blank
    add_area                               add a new Johnny Decimal area to `areas` or `resources`
    add_category                           add a new Johnny Decimal category to an existing area
    add_id                                 add a new Johnny Decimal ID to an existing category
    search                                 search the index by keyword or phrase

Arguments:
    systemName                             the name of the new system, e.g. "My Life"
    parentPath                             the path in which the system's root folder is created
    templateName                           a `04_templates` zip's basename, or "blank"
    projectTitle                           the new project's title
    domain                                 "areas" or "resources"
    area                                   an area reference, e.g. "10" or "10-19"
    category                               a category reference, e.g. "11"
    title                                  a title
    description                            a description
    term                                   a search word or phrase

Options:
    -h, --help                             show this help message
    -v, --version                          show version
    -s, --settings <pathToSettingsFile>    the settings file
"""

import os
import sys

from fundamentals import tools, times

from aardvark_jd import db, folders, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser
from aardvark_jd.new_project import new_project
from aardvark_jd.search import search, format_result

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
            try:
                _dispatch(a, log, indexDbConn)
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


def _dispatch(a, log, indexDbConn):
    """
    *dispatch to the relevant worker class for the parsed command, and print its result*

    **Key Arguments:**

    - ``a`` -- the friendly-named docopt arguments dict
    - ``log`` -- logger
    - ``indexDbConn`` -- an open SQLite connection to the active system's index
    """
    if a["new_project"]:
        title, folderPath, templateUsed = new_project(
            log=log, dbConn=indexDbConn, templateName=a["templateName"], projectTitle=a["projectTitle"],
        ).get()
        print(f"project '{title}' created at {folderPath} (template: {templateUsed})")

    elif a["add_area"]:
        code, folderPath = add_area(
            log=log, dbConn=indexDbConn, domain=a["domain"], title=a["title"], description=a["description"],
        ).get()
        print(f"{code}  {folderPath}")

    elif a["add_category"]:
        code, folderPath = add_category(
            log=log, dbConn=indexDbConn, domain=a["domain"], areaRef=a["area"],
            title=a["title"], description=a["description"],
        ).get()
        print(f"{code}  {folderPath}")

    elif a["add_id"]:
        code, folderPath = add_id(
            log=log, dbConn=indexDbConn, domain=a["domain"], categoryRef=a["category"],
            title=a["title"], description=a["description"],
        ).get()
        print(f"{code}  {folderPath}")

    elif a["search"]:
        results = search(log=log, dbConn=indexDbConn, terms=a["term"]).get()
        if not results:
            print("no matches found")
        for row in results:
            print(format_result(row))


if __name__ == "__main__":
    main()
