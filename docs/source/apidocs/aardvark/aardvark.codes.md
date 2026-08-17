# {py:mod}`aardvark.codes`

```{py:module} aardvark.codes
```

```{autodoc2-docstring} aardvark.codes
:allowtitles:
```

## Module Contents

### Functions

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`domain_letter <aardvark.codes.domain_letter>`
  - ```{autodoc2-docstring} aardvark.codes.domain_letter
    :summary:
    ```
* - {py:obj}`format_area_code <aardvark.codes.format_area_code>`
  - ```{autodoc2-docstring} aardvark.codes.format_area_code
    :summary:
    ```
* - {py:obj}`format_category_code <aardvark.codes.format_category_code>`
  - ```{autodoc2-docstring} aardvark.codes.format_category_code
    :summary:
    ```
* - {py:obj}`format_id_code <aardvark.codes.format_id_code>`
  - ```{autodoc2-docstring} aardvark.codes.format_id_code
    :summary:
    ```
* - {py:obj}`parse_area_ref <aardvark.codes.parse_area_ref>`
  - ```{autodoc2-docstring} aardvark.codes.parse_area_ref
    :summary:
    ```
* - {py:obj}`parse_category_ref <aardvark.codes.parse_category_ref>`
  - ```{autodoc2-docstring} aardvark.codes.parse_category_ref
    :summary:
    ```
* - {py:obj}`validate_domain <aardvark.codes.validate_domain>`
  - ```{autodoc2-docstring} aardvark.codes.validate_domain
    :summary:
    ```
````

### Data

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`DOMAINS <aardvark.codes.DOMAINS>`
  - ```{autodoc2-docstring} aardvark.codes.DOMAINS
    :summary:
    ```
* - {py:obj}`DOMAIN_LETTER <aardvark.codes.DOMAIN_LETTER>`
  - ```{autodoc2-docstring} aardvark.codes.DOMAIN_LETTER
    :summary:
    ```
````

### API

````{py:data} DOMAINS
:canonical: aardvark.codes.DOMAINS
:value: >
   ('areas', 'resources')

```{autodoc2-docstring} aardvark.codes.DOMAINS
```

````

````{py:data} DOMAIN_LETTER
:canonical: aardvark.codes.DOMAIN_LETTER
:value: >
   None

```{autodoc2-docstring} aardvark.codes.DOMAIN_LETTER
```

````

````{py:function} domain_letter(domain)
:canonical: aardvark.codes.domain_letter

```{autodoc2-docstring} aardvark.codes.domain_letter
```
````

````{py:function} format_area_code(domain, decadeStart, decadeEnd)
:canonical: aardvark.codes.format_area_code

```{autodoc2-docstring} aardvark.codes.format_area_code
```
````

````{py:function} format_category_code(domain, acNumber)
:canonical: aardvark.codes.format_category_code

```{autodoc2-docstring} aardvark.codes.format_category_code
```
````

````{py:function} format_id_code(domain, acNumber, itemNumber)
:canonical: aardvark.codes.format_id_code

```{autodoc2-docstring} aardvark.codes.format_id_code
```
````

````{py:function} parse_area_ref(text)
:canonical: aardvark.codes.parse_area_ref

```{autodoc2-docstring} aardvark.codes.parse_area_ref
```
````

````{py:function} parse_category_ref(text)
:canonical: aardvark.codes.parse_category_ref

```{autodoc2-docstring} aardvark.codes.parse_category_ref
```
````

````{py:function} validate_domain(domain)
:canonical: aardvark.codes.validate_domain

```{autodoc2-docstring} aardvark.codes.validate_domain
```
````
