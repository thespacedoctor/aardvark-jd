# {py:mod}`aardvark_jd.emoji_picker`

```{py:module} aardvark_jd.emoji_picker
```

```{autodoc2-docstring} aardvark_jd.emoji_picker
:allowtitles:
```

## Module Contents

### Functions

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`llm_enabled <aardvark_jd.emoji_picker.llm_enabled>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.llm_enabled
    :summary:
    ```
* - {py:obj}`pick_emoji <aardvark_jd.emoji_picker.pick_emoji>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.pick_emoji
    :summary:
    ```
* - {py:obj}`resolve_emoji <aardvark_jd.emoji_picker.resolve_emoji>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.resolve_emoji
    :summary:
    ```
* - {py:obj}`suggest_emoji <aardvark_jd.emoji_picker.suggest_emoji>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.suggest_emoji
    :summary:
    ```
* - {py:obj}`validate_chosen_emoji <aardvark_jd.emoji_picker.validate_chosen_emoji>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.validate_chosen_emoji
    :summary:
    ```
````

### Data

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`CLAUDE_EFFORT <aardvark_jd.emoji_picker.CLAUDE_EFFORT>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_EFFORT
    :summary:
    ```
* - {py:obj}`CLAUDE_MAX_RETRIES <aardvark_jd.emoji_picker.CLAUDE_MAX_RETRIES>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_MAX_RETRIES
    :summary:
    ```
* - {py:obj}`CLAUDE_MAX_TOKENS <aardvark_jd.emoji_picker.CLAUDE_MAX_TOKENS>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_MAX_TOKENS
    :summary:
    ```
* - {py:obj}`CLAUDE_MODEL <aardvark_jd.emoji_picker.CLAUDE_MODEL>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_MODEL
    :summary:
    ```
* - {py:obj}`CLAUDE_TIMEOUT_SECONDS <aardvark_jd.emoji_picker.CLAUDE_TIMEOUT_SECONDS>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_TIMEOUT_SECONDS
    :summary:
    ```
* - {py:obj}`FALLBACK_EMOJI <aardvark_jd.emoji_picker.FALLBACK_EMOJI>`
  - ```{autodoc2-docstring} aardvark_jd.emoji_picker.FALLBACK_EMOJI
    :summary:
    ```
````

### API

````{py:data} CLAUDE_EFFORT
:canonical: aardvark_jd.emoji_picker.CLAUDE_EFFORT
:value: >
   'low'

```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_EFFORT
```

````

````{py:data} CLAUDE_MAX_RETRIES
:canonical: aardvark_jd.emoji_picker.CLAUDE_MAX_RETRIES
:value: >
   0

```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_MAX_RETRIES
```

````

````{py:data} CLAUDE_MAX_TOKENS
:canonical: aardvark_jd.emoji_picker.CLAUDE_MAX_TOKENS
:value: >
   1024

```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_MAX_TOKENS
```

````

````{py:data} CLAUDE_MODEL
:canonical: aardvark_jd.emoji_picker.CLAUDE_MODEL
:value: >
   'claude-opus-5'

```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_MODEL
```

````

````{py:data} CLAUDE_TIMEOUT_SECONDS
:canonical: aardvark_jd.emoji_picker.CLAUDE_TIMEOUT_SECONDS
:value: >
   15.0

```{autodoc2-docstring} aardvark_jd.emoji_picker.CLAUDE_TIMEOUT_SECONDS
```

````

````{py:data} FALLBACK_EMOJI
:canonical: aardvark_jd.emoji_picker.FALLBACK_EMOJI
:value: >
   '📁'

```{autodoc2-docstring} aardvark_jd.emoji_picker.FALLBACK_EMOJI
```

````

````{py:function} llm_enabled(settings)
:canonical: aardvark_jd.emoji_picker.llm_enabled

```{autodoc2-docstring} aardvark_jd.emoji_picker.llm_enabled
```
````

````{py:function} pick_emoji(title, description='')
:canonical: aardvark_jd.emoji_picker.pick_emoji

```{autodoc2-docstring} aardvark_jd.emoji_picker.pick_emoji
```
````

````{py:function} resolve_emoji(title, description='', chosenEmoji=None, settings=None, log=None)
:canonical: aardvark_jd.emoji_picker.resolve_emoji

```{autodoc2-docstring} aardvark_jd.emoji_picker.resolve_emoji
```
````

````{py:function} suggest_emoji(title, description='', settings=None, log=None)
:canonical: aardvark_jd.emoji_picker.suggest_emoji

```{autodoc2-docstring} aardvark_jd.emoji_picker.suggest_emoji
```
````

````{py:function} validate_chosen_emoji(chosenEmoji)
:canonical: aardvark_jd.emoji_picker.validate_chosen_emoji

```{autodoc2-docstring} aardvark_jd.emoji_picker.validate_chosen_emoji
```
````
