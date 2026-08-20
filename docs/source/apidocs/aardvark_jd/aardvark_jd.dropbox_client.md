# {py:mod}`aardvark_jd.dropbox_client`

```{py:module} aardvark_jd.dropbox_client
```

```{autodoc2-docstring} aardvark_jd.dropbox_client
:allowtitles:
```

## Module Contents

### Classes

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`DropboxClient <aardvark_jd.dropbox_client.DropboxClient>`
  - ```{autodoc2-docstring} aardvark_jd.dropbox_client.DropboxClient
    :summary:
    ```
````

### Functions

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`find_containing_root <aardvark_jd.dropbox_client.find_containing_root>`
  - ```{autodoc2-docstring} aardvark_jd.dropbox_client.find_containing_root
    :summary:
    ```
* - {py:obj}`local_dropbox_roots <aardvark_jd.dropbox_client.local_dropbox_roots>`
  - ```{autodoc2-docstring} aardvark_jd.dropbox_client.local_dropbox_roots
    :summary:
    ```
* - {py:obj}`to_dropbox_path <aardvark_jd.dropbox_client.to_dropbox_path>`
  - ```{autodoc2-docstring} aardvark_jd.dropbox_client.to_dropbox_path
    :summary:
    ```
````

### API

`````{py:exception} DropboxApiError()
:canonical: aardvark_jd.dropbox_client.DropboxApiError

Bases: {py:obj}`Exception`

```{py:class} __cause__
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__cause__

```

```{py:class} __context__
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__context__

```

````{py:method} __delattr__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__delattr__

````

````{py:method} __dir__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__dir__

````

````{py:method} __eq__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__eq__

````

````{py:method} __format__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__format__

````

````{py:method} __ge__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__ge__

````

````{py:method} __getattribute__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__getattribute__

````

````{py:method} __getstate__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__getstate__

````

````{py:method} __gt__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__gt__

````

````{py:method} __hash__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__hash__

````

````{py:method} __le__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__le__

````

````{py:method} __lt__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__lt__

````

````{py:method} __ne__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__ne__

````

````{py:method} __new__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__new__

````

````{py:method} __reduce__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__reduce__

````

````{py:method} __reduce_ex__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__reduce_ex__

````

````{py:method} __repr__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__repr__

````

````{py:method} __setattr__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__setattr__

````

````{py:method} __setstate__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__setstate__

````

````{py:method} __sizeof__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__sizeof__

````

````{py:method} __str__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__str__

````

````{py:method} __subclasshook__()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__subclasshook__

````

```{py:class} __suppress_context__
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__suppress_context__

```

```{py:class} __traceback__
:canonical: aardvark_jd.dropbox_client.DropboxApiError.__traceback__

```

````{py:method} add_note()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.add_note

````

```{py:class} args
:canonical: aardvark_jd.dropbox_client.DropboxApiError.args

```

````{py:method} with_traceback()
:canonical: aardvark_jd.dropbox_client.DropboxApiError.with_traceback

````

`````

`````{py:class} DropboxClient(appKey, appSecret, refreshToken)
:canonical: aardvark_jd.dropbox_client.DropboxClient

Bases: {py:obj}`object`

```{autodoc2-docstring} aardvark_jd.dropbox_client.DropboxClient
```

```{rubric} Initialization
```

```{autodoc2-docstring} aardvark_jd.dropbox_client.DropboxClient.__init__
```

````{py:method} shared_link(dropboxPath)
:canonical: aardvark_jd.dropbox_client.DropboxClient.shared_link

```{autodoc2-docstring} aardvark_jd.dropbox_client.DropboxClient.shared_link
```

````

`````

````{py:function} find_containing_root(localPath, roots)
:canonical: aardvark_jd.dropbox_client.find_containing_root

```{autodoc2-docstring} aardvark_jd.dropbox_client.find_containing_root
```
````

````{py:function} local_dropbox_roots()
:canonical: aardvark_jd.dropbox_client.local_dropbox_roots

```{autodoc2-docstring} aardvark_jd.dropbox_client.local_dropbox_roots
```
````

````{py:function} to_dropbox_path(localPath, dropboxRoot)
:canonical: aardvark_jd.dropbox_client.to_dropbox_path

```{autodoc2-docstring} aardvark_jd.dropbox_client.to_dropbox_path
```
````
