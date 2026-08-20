# ZSH COMPLETION FOR aardvark / av
# INSTALL WITH:  eval "$(aardvark completion zsh)"
# OR CACHE IT:   aardvark completion zsh > ~/.zsh/completions/_aardvark
#compdef aardvark av
_aardvark() {
    local -a rawLines describePairs
    local line value description
    rawLines=(${(f)"$(aardvark __complete $((CURRENT-1)) ${words[@]} 2>/dev/null)"})
    for line in $rawLines; do
        [[ -z "$line" ]] && continue
        value="${line%%$'\t'*}"
        description="${line#*$'\t'}"
        if [[ "$description" == "$line" ]]; then
            describePairs+=("$value")
        else
            # `_describe` SPLITS ON THE FIRST COLON, SO ESCAPE ANY IN THE VALUE
            describePairs+=("${value//:/\\:}:$description")
        fi
    done
    if (( ${#describePairs} )); then
        _describe -t aardvark 'aardvark' describePairs
    else
        _files
    fi
}
compdef _aardvark aardvark av
