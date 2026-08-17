# {py:mod}`aardvark_jd.db`

```{py:module} aardvark_jd.db
```

```{autodoc2-docstring} aardvark_jd.db
:allowtitles:
```

## Module Contents

### Functions

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`fts5_enabled <aardvark_jd.db.fts5_enabled>`
  - ```{autodoc2-docstring} aardvark_jd.db.fts5_enabled
    :summary:
    ```
* - {py:obj}`get_area <aardvark_jd.db.get_area>`
  - ```{autodoc2-docstring} aardvark_jd.db.get_area
    :summary:
    ```
* - {py:obj}`get_category <aardvark_jd.db.get_category>`
  - ```{autodoc2-docstring} aardvark_jd.db.get_category
    :summary:
    ```
* - {py:obj}`get_connection <aardvark_jd.db.get_connection>`
  - ```{autodoc2-docstring} aardvark_jd.db.get_connection
    :summary:
    ```
* - {py:obj}`get_meta <aardvark_jd.db.get_meta>`
  - ```{autodoc2-docstring} aardvark_jd.db.get_meta
    :summary:
    ```
* - {py:obj}`get_system_folder <aardvark_jd.db.get_system_folder>`
  - ```{autodoc2-docstring} aardvark_jd.db.get_system_folder
    :summary:
    ```
* - {py:obj}`initialise_schema <aardvark_jd.db.initialise_schema>`
  - ```{autodoc2-docstring} aardvark_jd.db.initialise_schema
    :summary:
    ```
* - {py:obj}`insert_area <aardvark_jd.db.insert_area>`
  - ```{autodoc2-docstring} aardvark_jd.db.insert_area
    :summary:
    ```
* - {py:obj}`insert_category <aardvark_jd.db.insert_category>`
  - ```{autodoc2-docstring} aardvark_jd.db.insert_category
    :summary:
    ```
* - {py:obj}`insert_id <aardvark_jd.db.insert_id>`
  - ```{autodoc2-docstring} aardvark_jd.db.insert_id
    :summary:
    ```
* - {py:obj}`insert_project <aardvark_jd.db.insert_project>`
  - ```{autodoc2-docstring} aardvark_jd.db.insert_project
    :summary:
    ```
* - {py:obj}`insert_system_folder <aardvark_jd.db.insert_system_folder>`
  - ```{autodoc2-docstring} aardvark_jd.db.insert_system_folder
    :summary:
    ```
* - {py:obj}`list_areas <aardvark_jd.db.list_areas>`
  - ```{autodoc2-docstring} aardvark_jd.db.list_areas
    :summary:
    ```
* - {py:obj}`list_categories <aardvark_jd.db.list_categories>`
  - ```{autodoc2-docstring} aardvark_jd.db.list_categories
    :summary:
    ```
* - {py:obj}`list_ids <aardvark_jd.db.list_ids>`
  - ```{autodoc2-docstring} aardvark_jd.db.list_ids
    :summary:
    ```
* - {py:obj}`set_meta <aardvark_jd.db.set_meta>`
  - ```{autodoc2-docstring} aardvark_jd.db.set_meta
    :summary:
    ```
````

### API

````{py:function} fts5_enabled(dbConn)
:canonical: aardvark_jd.db.fts5_enabled

```{autodoc2-docstring} aardvark_jd.db.fts5_enabled
```
````

````{py:function} get_area(dbConn, domain, decadeStart)
:canonical: aardvark_jd.db.get_area

```{autodoc2-docstring} aardvark_jd.db.get_area
```
````

````{py:function} get_category(dbConn, domain, acNumber)
:canonical: aardvark_jd.db.get_category

```{autodoc2-docstring} aardvark_jd.db.get_category
```
````

````{py:function} get_connection(pathToDb)
:canonical: aardvark_jd.db.get_connection

```{autodoc2-docstring} aardvark_jd.db.get_connection
```
````

````{py:function} get_meta(dbConn, key)
:canonical: aardvark_jd.db.get_meta

```{autodoc2-docstring} aardvark_jd.db.get_meta
```
````

````{py:function} get_system_folder(dbConn, folderKey)
:canonical: aardvark_jd.db.get_system_folder

```{autodoc2-docstring} aardvark_jd.db.get_system_folder
```
````

````{py:function} initialise_schema(dbConn)
:canonical: aardvark_jd.db.initialise_schema

```{autodoc2-docstring} aardvark_jd.db.initialise_schema
```
````

````{py:function} insert_area(dbConn, domain, decadeStart, decadeEnd, title, description, emoji, folderName, folderPath)
:canonical: aardvark_jd.db.insert_area

```{autodoc2-docstring} aardvark_jd.db.insert_area
```
````

````{py:function} insert_category(dbConn, areaId, domain, acNumber, title, description, emoji, folderName, folderPath)
:canonical: aardvark_jd.db.insert_category

```{autodoc2-docstring} aardvark_jd.db.insert_category
```
````

````{py:function} insert_id(dbConn, categoryId, domain, acNumber, itemNumber, title, description, folderName, folderPath)
:canonical: aardvark_jd.db.insert_id

```{autodoc2-docstring} aardvark_jd.db.insert_id
```
````

````{py:function} insert_project(dbConn, title, description, emoji, folderName, folderPath, templateUsed)
:canonical: aardvark_jd.db.insert_project

```{autodoc2-docstring} aardvark_jd.db.insert_project
```
````

````{py:function} insert_system_folder(dbConn, folderKey, folderName, folderPath)
:canonical: aardvark_jd.db.insert_system_folder

```{autodoc2-docstring} aardvark_jd.db.insert_system_folder
```
````

````{py:function} list_areas(dbConn, domain)
:canonical: aardvark_jd.db.list_areas

```{autodoc2-docstring} aardvark_jd.db.list_areas
```
````

````{py:function} list_categories(dbConn, domain, areaId=None)
:canonical: aardvark_jd.db.list_categories

```{autodoc2-docstring} aardvark_jd.db.list_categories
```
````

````{py:function} list_ids(dbConn, domain, categoryId)
:canonical: aardvark_jd.db.list_ids

```{autodoc2-docstring} aardvark_jd.db.list_ids
```
````

````{py:function} set_meta(dbConn, key, value)
:canonical: aardvark_jd.db.set_meta

```{autodoc2-docstring} aardvark_jd.db.set_meta
```
````
