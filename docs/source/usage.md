

```bash
    
    Documentation for aardvark can be found here: http://aardvark.readthedocs.org
    
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
    

```
