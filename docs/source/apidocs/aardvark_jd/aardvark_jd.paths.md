# {py:mod}`aardvark_jd.paths`

```{py:module} aardvark_jd.paths
```

```{autodoc2-docstring} aardvark_jd.paths
:allowtitles:
```

## Module Contents

### Functions

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`find_db_path <aardvark_jd.paths.find_db_path>`
  - ```{autodoc2-docstring} aardvark_jd.paths.find_db_path
    :summary:
    ```
* - {py:obj}`get_db_path_in_folder <aardvark_jd.paths.get_db_path_in_folder>`
  - ```{autodoc2-docstring} aardvark_jd.paths.get_db_path_in_folder
    :summary:
    ```
* - {py:obj}`resolve <aardvark_jd.paths.resolve>`
  - ```{autodoc2-docstring} aardvark_jd.paths.resolve
    :summary:
    ```
* - {py:obj}`skeleton_entry <aardvark_jd.paths.skeleton_entry>`
  - ```{autodoc2-docstring} aardvark_jd.paths.skeleton_entry
    :summary:
    ```
````

### Data

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`DB_BASENAME <aardvark_jd.paths.DB_BASENAME>`
  - ```{autodoc2-docstring} aardvark_jd.paths.DB_BASENAME
    :summary:
    ```
* - {py:obj}`SYSTEM_FOLDER_EMOJI <aardvark_jd.paths.SYSTEM_FOLDER_EMOJI>`
  - ```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_FOLDER_EMOJI
    :summary:
    ```
* - {py:obj}`SYSTEM_SKELETON <aardvark_jd.paths.SYSTEM_SKELETON>`
  - ```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SKELETON
    :summary:
    ```
* - {py:obj}`SYSTEM_SUBFOLDERS <aardvark_jd.paths.SYSTEM_SUBFOLDERS>`
  - ```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SUBFOLDERS
    :summary:
    ```
* - {py:obj}`SYSTEM_SUBFOLDER_KIND_DOCUMENT <aardvark_jd.paths.SYSTEM_SUBFOLDER_KIND_DOCUMENT>`
  - ```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SUBFOLDER_KIND_DOCUMENT
    :summary:
    ```
* - {py:obj}`SYSTEM_SUBFOLDER_KIND_FOLDER <aardvark_jd.paths.SYSTEM_SUBFOLDER_KIND_FOLDER>`
  - ```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SUBFOLDER_KIND_FOLDER
    :summary:
    ```
````

### API

````{py:data} DB_BASENAME
:canonical: aardvark_jd.paths.DB_BASENAME
:value: >
   'aardvark.db'

```{autodoc2-docstring} aardvark_jd.paths.DB_BASENAME
```

````

````{py:data} SYSTEM_FOLDER_EMOJI
:canonical: aardvark_jd.paths.SYSTEM_FOLDER_EMOJI
:value: >
   '⚙️'

```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_FOLDER_EMOJI
```

````

````{py:data} SYSTEM_SKELETON
:canonical: aardvark_jd.paths.SYSTEM_SKELETON
:value: >
   [('root.index', None, '00_INDEX', 'Index', 'The aardvark database and system index', '🗂️'), ('root.i...

```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SKELETON
```

````

````{py:data} SYSTEM_SUBFOLDERS
:canonical: aardvark_jd.paths.SYSTEM_SUBFOLDERS
:value: >
   [('00_index', 'Index', 'The index for this section', '🗂️'), ('01_inbox', 'Inbox', 'Unsorted items aw...

```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SUBFOLDERS
```

````

````{py:data} SYSTEM_SUBFOLDER_KIND_DOCUMENT
:canonical: aardvark_jd.paths.SYSTEM_SUBFOLDER_KIND_DOCUMENT
:value: >
   'document'

```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SUBFOLDER_KIND_DOCUMENT
```

````

````{py:data} SYSTEM_SUBFOLDER_KIND_FOLDER
:canonical: aardvark_jd.paths.SYSTEM_SUBFOLDER_KIND_FOLDER
:value: >
   'folder'

```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SUBFOLDER_KIND_FOLDER
```

````

````{py:function} find_db_path(rootPath)
:canonical: aardvark_jd.paths.find_db_path

```{autodoc2-docstring} aardvark_jd.paths.find_db_path
```
````

````{py:function} get_db_path_in_folder(indexFolderPath)
:canonical: aardvark_jd.paths.get_db_path_in_folder

```{autodoc2-docstring} aardvark_jd.paths.get_db_path_in_folder
```
````

````{py:function} resolve(dbConn, folderKey)
:canonical: aardvark_jd.paths.resolve

```{autodoc2-docstring} aardvark_jd.paths.resolve
```
````

````{py:function} skeleton_entry(folderKey)
:canonical: aardvark_jd.paths.skeleton_entry

```{autodoc2-docstring} aardvark_jd.paths.skeleton_entry
```
````
