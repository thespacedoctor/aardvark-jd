# BASH COMPLETION FOR aardvark / av
# INSTALL WITH:  eval "$(aardvark completion bash)"
_aardvark_complete() {
    local IFS=$'\n'
    local line candidate
    COMPREPLY=()
    for line in $(aardvark __complete "$COMP_CWORD" "${COMP_WORDS[@]}" 2>/dev/null); do
        # STRIP THE TAB-SEPARATED DESCRIPTION - BASH HAS NOWHERE TO SHOW IT
        candidate="${line%%$'\t'*}"
        [ -n "$candidate" ] && COMPREPLY+=("$candidate")
    done
    # WITH NO CANDIDATES OF OUR OWN, FALL BACK TO FILENAMES (`-o default`)
    return 0
}
complete -o default -F _aardvark_complete aardvark av
