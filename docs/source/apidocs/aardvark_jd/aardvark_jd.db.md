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

* - {py:obj}`entity_rows_for_path_prefix <aardvark_jd.db.entity_rows_for_path_prefix>`
  - ```{autodoc2-docstring} aardvark_jd.db.entity_rows_for_path_prefix
    :summary:
    ```
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
* - {py:obj}`get_craft_link <aardvark_jd.db.get_craft_link>`
  - ```{autodoc2-docstring} aardvark_jd.db.get_craft_link
    :summary:
    ```
* - {py:obj}`get_dropbox_link <aardvark_jd.db.get_dropbox_link>`
  - ```{autodoc2-docstring} aardvark_jd.db.get_dropbox_link
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
* - {py:obj}`list_system_folders <aardvark_jd.db.list_system_folders>`
  - ```{autodoc2-docstring} aardvark_jd.db.list_system_folders
    :summary:
    ```
* - {py:obj}`rewrite_folder_path_prefix <aardvark_jd.db.rewrite_folder_path_prefix>`
  - ```{autodoc2-docstring} aardvark_jd.db.rewrite_folder_path_prefix
    :summary:
    ```
* - {py:obj}`set_meta <aardvark_jd.db.set_meta>`
  - ```{autodoc2-docstring} aardvark_jd.db.set_meta
    :summary:
    ```
* - {py:obj}`update_area_emoji <aardvark_jd.db.update_area_emoji>`
  - ```{autodoc2-docstring} aardvark_jd.db.update_area_emoji
    :summary:
    ```
* - {py:obj}`update_category_emoji <aardvark_jd.db.update_category_emoji>`
  - ```{autodoc2-docstring} aardvark_jd.db.update_category_emoji
    :summary:
    ```
* - {py:obj}`update_id_name <aardvark_jd.db.update_id_name>`
  - ```{autodoc2-docstring} aardvark_jd.db.update_id_name
    :summary:
    ```
* - {py:obj}`update_system_folder <aardvark_jd.db.update_system_folder>`
  - ```{autodoc2-docstring} aardvark_jd.db.update_system_folder
    :summary:
    ```
* - {py:obj}`upsert_craft_link <aardvark_jd.db.upsert_craft_link>`
  - ```{autodoc2-docstring} aardvark_jd.db.upsert_craft_link
    :summary:
    ```
* - {py:obj}`upsert_dropbox_link <aardvark_jd.db.upsert_dropbox_link>`
  - ```{autodoc2-docstring} aardvark_jd.db.upsert_dropbox_link
    :summary:
    ```
````

### API

````{py:function} entity_rows_for_path_prefix(dbConn)
:canonical: aardvark_jd.db.entity_rows_for_path_prefix

```{autodoc2-docstring} aardvark_jd.db.entity_rows_for_path_prefix
```
````

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

````{py:function} get_craft_link(dbConn, entityType, entityKey)
:canonical: aardvark_jd.db.get_craft_link

```{autodoc2-docstring} aardvark_jd.db.get_craft_link
```
````

````{py:function} get_dropbox_link(dbConn, folderPath)
:canonical: aardvark_jd.db.get_dropbox_link

```{autodoc2-docstring} aardvark_jd.db.get_dropbox_link
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

````{py:function} list_system_folders(dbConn)
:canonical: aardvark_jd.db.list_system_folders

```{autodoc2-docstring} aardvark_jd.db.list_system_folders
```
````

````{py:function} rewrite_folder_path_prefix(dbConn, oldPrefix, newPrefix)
:canonical: aardvark_jd.db.rewrite_folder_path_prefix

```{autodoc2-docstring} aardvark_jd.db.rewrite_folder_path_prefix
```
````

````{py:function} set_meta(dbConn, key, value)
:canonical: aardvark_jd.db.set_meta

```{autodoc2-docstring} aardvark_jd.db.set_meta
```
````

````{py:function} update_area_emoji(dbConn, areaId, emoji, folderName, folderPath)
:canonical: aardvark_jd.db.update_area_emoji

```{autodoc2-docstring} aardvark_jd.db.update_area_emoji
```
````

````{py:function} update_category_emoji(dbConn, categoryId, emoji, folderName, folderPath)
:canonical: aardvark_jd.db.update_category_emoji

```{autodoc2-docstring} aardvark_jd.db.update_category_emoji
```
````

````{py:function} update_id_name(dbConn, idId, folderName, folderPath)
:canonical: aardvark_jd.db.update_id_name

```{autodoc2-docstring} aardvark_jd.db.update_id_name
```
````

````{py:function} update_system_folder(dbConn, folderKey, folderName, folderPath)
:canonical: aardvark_jd.db.update_system_folder

```{autodoc2-docstring} aardvark_jd.db.update_system_folder
```
````

````{py:function} upsert_craft_link(dbConn, entityType, entityKey, craftFolderId=None, craftDocumentId=None, craftBlockId=None, craftUrl=None, linksMarkdown=None, clearBlockId=False)
:canonical: aardvark_jd.db.upsert_craft_link

```{autodoc2-docstring} aardvark_jd.db.upsert_craft_link
```
````

````{py:function} upsert_dropbox_link(dbConn, folderPath, dropboxUrl)
:canonical: aardvark_jd.db.upsert_dropbox_link

```{autodoc2-docstring} aardvark_jd.db.upsert_dropbox_link
```
````
