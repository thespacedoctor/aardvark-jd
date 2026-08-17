# {py:mod}`aardvark.paths`

```{py:module} aardvark.paths
```

```{autodoc2-docstring} aardvark.paths
:allowtitles:
```

## Module Contents

### Functions

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`find_db_path <aardvark.paths.find_db_path>`
  - ```{autodoc2-docstring} aardvark.paths.find_db_path
    :summary:
    ```
* - {py:obj}`get_db_path_in_folder <aardvark.paths.get_db_path_in_folder>`
  - ```{autodoc2-docstring} aardvark.paths.get_db_path_in_folder
    :summary:
    ```
* - {py:obj}`resolve <aardvark.paths.resolve>`
  - ```{autodoc2-docstring} aardvark.paths.resolve
    :summary:
    ```
````

### Data

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`DB_BASENAME <aardvark.paths.DB_BASENAME>`
  - ```{autodoc2-docstring} aardvark.paths.DB_BASENAME
    :summary:
    ```
* - {py:obj}`SYSTEM_SKELETON <aardvark.paths.SYSTEM_SKELETON>`
  - ```{autodoc2-docstring} aardvark.paths.SYSTEM_SKELETON
    :summary:
    ```
````

### API

````{py:data} DB_BASENAME
:canonical: aardvark.paths.DB_BASENAME
:value: >
   'aardvark.db'

```{autodoc2-docstring} aardvark.paths.DB_BASENAME
```

````

````{py:data} SYSTEM_SKELETON
:canonical: aardvark.paths.SYSTEM_SKELETON
:value: >
   [('root.index', None, '00_index', 'Index', 'The aardvark database and system index'), ('root.inbox',...

```{autodoc2-docstring} aardvark.paths.SYSTEM_SKELETON
```

````

````{py:function} find_db_path(rootPath)
:canonical: aardvark.paths.find_db_path

```{autodoc2-docstring} aardvark.paths.find_db_path
```
````

````{py:function} get_db_path_in_folder(indexFolderPath)
:canonical: aardvark.paths.get_db_path_in_folder

```{autodoc2-docstring} aardvark.paths.get_db_path_in_folder
```
````

````{py:function} resolve(dbConn, folderKey)
:canonical: aardvark.paths.resolve

```{autodoc2-docstring} aardvark.paths.resolve
```
````
