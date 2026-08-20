

```bash
    
    Documentation for aardvark can be found here: http://aardvark-jd.readthedocs.org
    
    Usage:
        aardvark init <systemName> <parentPath> [-s <pathToSettingsFile>]
        aardvark new_project <category> [<templateName>] [<projectTitle>] [-s <pathToSettingsFile>]
        aardvark add_area <domainLetter> <title> <description> [-e <emoji>] [-s <pathToSettingsFile>]
        aardvark add_category <area> <title> <description> [-e <emoji>] [-s <pathToSettingsFile>]
        aardvark add_id <category> <title> <description> [-s <pathToSettingsFile>]
        aardvark set_emoji <ref> <emoji> [-s <pathToSettingsFile>]
        aardvark repair_emoji [-s <pathToSettingsFile>]
        aardvark search <term>... [-s <pathToSettingsFile>]
        aardvark connect_craft <apiUrl> <apiToken> [-s <pathToSettingsFile>]
        aardvark craft_sync [-s <pathToSettingsFile>]
        aardvark connect_dropbox <appKey> <appSecret> [-s <pathToSettingsFile>]
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
        open                                   open the Craft folder/document that mirrors a filesystem path (default: the current directory)
    
    Arguments:
        systemName                             the name of the new system, e.g. "My Life"
        parentPath                             the path in which the system's root folder is created
        templateName                           a `04_templates` zip's basename, or "blank"
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
        apiToken                               a craft.do API connection token
        appKey                                 a Dropbox app's key, from the App Console
        appSecret                              a Dropbox app's secret, from the App Console
        path                                   a filesystem path to resolve to its Craft document/folder (default: the current directory)
    
    Options:
        -h, --help                             show this help message
        -v, --version                          show version
        -e, --emoji <emoji>                    the emoji to use, skipping the suggestion and prompt
        -s, --settings <pathToSettingsFile>    the settings file
    

```
