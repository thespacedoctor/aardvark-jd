# {py:mod}`aardvark_jd.codes`

```{py:module} aardvark_jd.codes
```

```{autodoc2-docstring} aardvark_jd.codes
:allowtitles:
```

## Module Contents

### Functions

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`domain_from_letter <aardvark_jd.codes.domain_from_letter>`
  - ```{autodoc2-docstring} aardvark_jd.codes.domain_from_letter
    :summary:
    ```
* - {py:obj}`domain_from_ref <aardvark_jd.codes.domain_from_ref>`
  - ```{autodoc2-docstring} aardvark_jd.codes.domain_from_ref
    :summary:
    ```
* - {py:obj}`domain_letter <aardvark_jd.codes.domain_letter>`
  - ```{autodoc2-docstring} aardvark_jd.codes.domain_letter
    :summary:
    ```
* - {py:obj}`format_area_code <aardvark_jd.codes.format_area_code>`
  - ```{autodoc2-docstring} aardvark_jd.codes.format_area_code
    :summary:
    ```
* - {py:obj}`format_category_code <aardvark_jd.codes.format_category_code>`
  - ```{autodoc2-docstring} aardvark_jd.codes.format_category_code
    :summary:
    ```
* - {py:obj}`format_id_code <aardvark_jd.codes.format_id_code>`
  - ```{autodoc2-docstring} aardvark_jd.codes.format_id_code
    :summary:
    ```
* - {py:obj}`is_jd_ref <aardvark_jd.codes.is_jd_ref>`
  - ```{autodoc2-docstring} aardvark_jd.codes.is_jd_ref
    :summary:
    ```
* - {py:obj}`parse_area_ref <aardvark_jd.codes.parse_area_ref>`
  - ```{autodoc2-docstring} aardvark_jd.codes.parse_area_ref
    :summary:
    ```
* - {py:obj}`parse_area_ref_is_area <aardvark_jd.codes.parse_area_ref_is_area>`
  - ```{autodoc2-docstring} aardvark_jd.codes.parse_area_ref_is_area
    :summary:
    ```
* - {py:obj}`parse_category_ref <aardvark_jd.codes.parse_category_ref>`
  - ```{autodoc2-docstring} aardvark_jd.codes.parse_category_ref
    :summary:
    ```
* - {py:obj}`split_area_ref <aardvark_jd.codes.split_area_ref>`
  - ```{autodoc2-docstring} aardvark_jd.codes.split_area_ref
    :summary:
    ```
* - {py:obj}`split_category_ref <aardvark_jd.codes.split_category_ref>`
  - ```{autodoc2-docstring} aardvark_jd.codes.split_category_ref
    :summary:
    ```
* - {py:obj}`validate_domain <aardvark_jd.codes.validate_domain>`
  - ```{autodoc2-docstring} aardvark_jd.codes.validate_domain
    :summary:
    ```
````

### Data

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`DOMAINS <aardvark_jd.codes.DOMAINS>`
  - ```{autodoc2-docstring} aardvark_jd.codes.DOMAINS
    :summary:
    ```
* - {py:obj}`DOMAIN_LETTER <aardvark_jd.codes.DOMAIN_LETTER>`
  - ```{autodoc2-docstring} aardvark_jd.codes.DOMAIN_LETTER
    :summary:
    ```
* - {py:obj}`LETTER_DOMAIN <aardvark_jd.codes.LETTER_DOMAIN>`
  - ```{autodoc2-docstring} aardvark_jd.codes.LETTER_DOMAIN
    :summary:
    ```
* - {py:obj}`LETTER_HINT <aardvark_jd.codes.LETTER_HINT>`
  - ```{autodoc2-docstring} aardvark_jd.codes.LETTER_HINT
    :summary:
    ```
````

### API

````{py:data} DOMAINS
:canonical: aardvark_jd.codes.DOMAINS
:value: >
   ('areas', 'resources', 'projects')

```{autodoc2-docstring} aardvark_jd.codes.DOMAINS
```

````

````{py:data} DOMAIN_LETTER
:canonical: aardvark_jd.codes.DOMAIN_LETTER
:value: >
   None

```{autodoc2-docstring} aardvark_jd.codes.DOMAIN_LETTER
```

````

````{py:data} LETTER_DOMAIN
:canonical: aardvark_jd.codes.LETTER_DOMAIN
:value: >
   None

```{autodoc2-docstring} aardvark_jd.codes.LETTER_DOMAIN
```

````

````{py:data} LETTER_HINT
:canonical: aardvark_jd.codes.LETTER_HINT
:value: >
   "'A' (areas), 'R' (resources) or 'P' (projects)"

```{autodoc2-docstring} aardvark_jd.codes.LETTER_HINT
```

````

````{py:function} domain_from_letter(text)
:canonical: aardvark_jd.codes.domain_from_letter

```{autodoc2-docstring} aardvark_jd.codes.domain_from_letter
```
````

````{py:function} domain_from_ref(text)
:canonical: aardvark_jd.codes.domain_from_ref

```{autodoc2-docstring} aardvark_jd.codes.domain_from_ref
```
````

````{py:function} domain_letter(domain)
:canonical: aardvark_jd.codes.domain_letter

```{autodoc2-docstring} aardvark_jd.codes.domain_letter
```
````

````{py:function} format_area_code(domain, decadeStart, decadeEnd)
:canonical: aardvark_jd.codes.format_area_code

```{autodoc2-docstring} aardvark_jd.codes.format_area_code
```
````

````{py:function} format_category_code(domain, acNumber)
:canonical: aardvark_jd.codes.format_category_code

```{autodoc2-docstring} aardvark_jd.codes.format_category_code
```
````

````{py:function} format_id_code(domain, acNumber, itemNumber)
:canonical: aardvark_jd.codes.format_id_code

```{autodoc2-docstring} aardvark_jd.codes.format_id_code
```
````

````{py:function} is_jd_ref(text)
:canonical: aardvark_jd.codes.is_jd_ref

```{autodoc2-docstring} aardvark_jd.codes.is_jd_ref
```
````

````{py:function} parse_area_ref(text, domain=None)
:canonical: aardvark_jd.codes.parse_area_ref

```{autodoc2-docstring} aardvark_jd.codes.parse_area_ref
```
````

````{py:function} parse_area_ref_is_area(text, domain=None)
:canonical: aardvark_jd.codes.parse_area_ref_is_area

```{autodoc2-docstring} aardvark_jd.codes.parse_area_ref_is_area
```
````

````{py:function} parse_category_ref(text, domain=None)
:canonical: aardvark_jd.codes.parse_category_ref

```{autodoc2-docstring} aardvark_jd.codes.parse_category_ref
```
````

````{py:function} split_area_ref(text, domain=None)
:canonical: aardvark_jd.codes.split_area_ref

```{autodoc2-docstring} aardvark_jd.codes.split_area_ref
```
````

````{py:function} split_category_ref(text, domain=None)
:canonical: aardvark_jd.codes.split_category_ref

```{autodoc2-docstring} aardvark_jd.codes.split_category_ref
```
````

````{py:function} validate_domain(domain)
:canonical: aardvark_jd.codes.validate_domain

```{autodoc2-docstring} aardvark_jd.codes.validate_domain
```
````
