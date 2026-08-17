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
* - {py:obj}`SYSTEM_SKELETON <aardvark_jd.paths.SYSTEM_SKELETON>`
  - ```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SKELETON
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

````{py:data} SYSTEM_SKELETON
:canonical: aardvark_jd.paths.SYSTEM_SKELETON
:value: >
   [('root.index', None, '00_INDEX', 'Index', 'The aardvark database and system index', '🗂️'), ('root.i...

```{autodoc2-docstring} aardvark_jd.paths.SYSTEM_SKELETON
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
