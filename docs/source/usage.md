

```bash
    
    Documentation for aardvark can be found here: http://aardvark-jd.readthedocs.org
    
    Usage:
        aardvark init <systemName> <parentPath> [-s <pathToSettingsFile>]
        aardvark new_project <category> [<templateName>] [<projectTitle>] [-s <pathToSettingsFile>]
        aardvark add_area <domain> <title> <description> [-e <emoji>] [-s <pathToSettingsFile>]
        aardvark add_category <domain> <area> <title> <description> [-e <emoji>] [-s <pathToSettingsFile>]
        aardvark add_id <domain> <category> <title> <description> [-s <pathToSettingsFile>]
        aardvark set_emoji <domain> <ref> <emoji> [-s <pathToSettingsFile>]
        aardvark repair_emoji [-s <pathToSettingsFile>]
        aardvark search <term>... [-s <pathToSettingsFile>]
        aardvark connect_craft <apiUrl> <apiToken> [-s <pathToSettingsFile>]
        aardvark craft_sync [-s <pathToSettingsFile>]
    
    Commands:
        init                                   create a new PARA + Johnny Decimal root and index
        new_project                            create a new project (a Johnny Decimal ID) in an existing project category, from a template or blank
        add_area                               add a new Johnny Decimal area to `areas` or `resources`
        add_category                           add a new Johnny Decimal category to an existing area
        add_id                                 add a new Johnny Decimal ID to an existing category
        set_emoji                              change the emoji on an existing folder, moving it and repointing the index
        repair_emoji                           fix drifted folder names/emoji and backfill missing reserved scaffolding
        search                                 search the index by keyword or phrase
        connect_craft                          connect a craft.do space and run the initial full mirror
        craft_sync                             re-run the craft.do mirror on demand, to backfill or repair drift
    
    Arguments:
        systemName                             the name of the new system, e.g. "My Life"
        parentPath                             the path in which the system's root folder is created
        templateName                           a `04_templates` zip's basename, or "blank"
        projectTitle                           the new project's title
        domain                                 "areas", "resources" or "projects"; set_emoji also takes "system"
        area                                   an area reference, e.g. "10" or "10-19"
        category                               a category reference, e.g. "11"
        ref                                    what to retarget: an area ("10"), category ("11"), or system folder key ("root.areas")
        emoji                                  an emoji character
        title                                  a title
        description                            a description
        term                                   a search word or phrase
        apiUrl                                 a craft.do API connection's unique base URL
        apiToken                               a craft.do API connection token
    
    Options:
        -h, --help                             show this help message
        -v, --version                          show version
        -e, --emoji <emoji>                    the emoji to use, skipping the suggestion and prompt
        -s, --settings <pathToSettingsFile>    the settings file
    

```
