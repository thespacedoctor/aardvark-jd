# {py:mod}`aardvark_jd.craft_client`

```{py:module} aardvark_jd.craft_client
```

```{autodoc2-docstring} aardvark_jd.craft_client
:allowtitles:
```

## Module Contents

### Classes

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`CraftClient <aardvark_jd.craft_client.CraftClient>`
  - ```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient
    :summary:
    ```
````

### API

`````{py:exception} CraftApiError()
:canonical: aardvark_jd.craft_client.CraftApiError

Bases: {py:obj}`Exception`

```{py:class} __cause__
:canonical: aardvark_jd.craft_client.CraftApiError.__cause__

```

```{py:class} __context__
:canonical: aardvark_jd.craft_client.CraftApiError.__context__

```

````{py:method} __delattr__()
:canonical: aardvark_jd.craft_client.CraftApiError.__delattr__

````

````{py:method} __dir__()
:canonical: aardvark_jd.craft_client.CraftApiError.__dir__

````

````{py:method} __eq__()
:canonical: aardvark_jd.craft_client.CraftApiError.__eq__

````

````{py:method} __format__()
:canonical: aardvark_jd.craft_client.CraftApiError.__format__

````

````{py:method} __ge__()
:canonical: aardvark_jd.craft_client.CraftApiError.__ge__

````

````{py:method} __getattribute__()
:canonical: aardvark_jd.craft_client.CraftApiError.__getattribute__

````

````{py:method} __getstate__()
:canonical: aardvark_jd.craft_client.CraftApiError.__getstate__

````

````{py:method} __gt__()
:canonical: aardvark_jd.craft_client.CraftApiError.__gt__

````

````{py:method} __hash__()
:canonical: aardvark_jd.craft_client.CraftApiError.__hash__

````

````{py:method} __le__()
:canonical: aardvark_jd.craft_client.CraftApiError.__le__

````

````{py:method} __lt__()
:canonical: aardvark_jd.craft_client.CraftApiError.__lt__

````

````{py:method} __ne__()
:canonical: aardvark_jd.craft_client.CraftApiError.__ne__

````

````{py:method} __new__()
:canonical: aardvark_jd.craft_client.CraftApiError.__new__

````

````{py:method} __reduce__()
:canonical: aardvark_jd.craft_client.CraftApiError.__reduce__

````

````{py:method} __reduce_ex__()
:canonical: aardvark_jd.craft_client.CraftApiError.__reduce_ex__

````

````{py:method} __repr__()
:canonical: aardvark_jd.craft_client.CraftApiError.__repr__

````

````{py:method} __setattr__()
:canonical: aardvark_jd.craft_client.CraftApiError.__setattr__

````

````{py:method} __setstate__()
:canonical: aardvark_jd.craft_client.CraftApiError.__setstate__

````

````{py:method} __sizeof__()
:canonical: aardvark_jd.craft_client.CraftApiError.__sizeof__

````

````{py:method} __str__()
:canonical: aardvark_jd.craft_client.CraftApiError.__str__

````

````{py:method} __subclasshook__()
:canonical: aardvark_jd.craft_client.CraftApiError.__subclasshook__

````

```{py:class} __suppress_context__
:canonical: aardvark_jd.craft_client.CraftApiError.__suppress_context__

```

```{py:class} __traceback__
:canonical: aardvark_jd.craft_client.CraftApiError.__traceback__

```

````{py:method} add_note()
:canonical: aardvark_jd.craft_client.CraftApiError.add_note

````

```{py:class} args
:canonical: aardvark_jd.craft_client.CraftApiError.args

```

````{py:method} with_traceback()
:canonical: aardvark_jd.craft_client.CraftApiError.with_traceback

````

`````

`````{py:class} CraftClient(apiUrl, apiToken)
:canonical: aardvark_jd.craft_client.CraftClient

Bases: {py:obj}`object`

```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient
```

```{rubric} Initialization
```

```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient.__init__
```

````{py:method} add_block(documentId, markdown, position='end')
:canonical: aardvark_jd.craft_client.CraftClient.add_block

```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient.add_block
```

````

````{py:method} create_document(title, folderId=None)
:canonical: aardvark_jd.craft_client.CraftClient.create_document

```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient.create_document
```

````

````{py:method} create_folder(name, parentFolderId=None)
:canonical: aardvark_jd.craft_client.CraftClient.create_folder

```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient.create_folder
```

````

````{py:method} delete_blocks(blockIds)
:canonical: aardvark_jd.craft_client.CraftClient.delete_blocks

```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient.delete_blocks
```

````

````{py:method} folder_deep_link(folderId, title)
:canonical: aardvark_jd.craft_client.CraftClient.folder_deep_link

```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient.folder_deep_link
```

````

````{py:method} get_block(blockId)
:canonical: aardvark_jd.craft_client.CraftClient.get_block

```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient.get_block
```

````

````{py:method} list_folders()
:canonical: aardvark_jd.craft_client.CraftClient.list_folders

```{autodoc2-docstring} aardvark_jd.craft_client.CraftClient.list_folders
```

````

`````
