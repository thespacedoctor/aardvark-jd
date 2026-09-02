# AARDVARK SHELL INTEGRATION - MAKES `av cd <target>` MOVE THIS SHELL
# INSTALL WITH:  eval "$(aardvark shell_init bash)"
# THIS SUPERSEDES `eval "$(aardvark completion bash)"` - IT ALREADY EMITS
# THE SAME COMPLETION SCRIPT BELOW ITS OWN OUTPUT.
#
# A SUBPROCESS CANNOT CHANGE ITS PARENT SHELL'S WORKING DIRECTORY, SO
# `aardvark cd <target>` ITSELF ONLY PRINTS THE RESOLVED PATH. THIS
# WRAPPER CATCHES THE `cd` SUBCOMMAND AND DOES THE ACTUAL `builtin cd`;
# EVERY OTHER SUBCOMMAND PASSES THROUGH UNCHANGED. `command` BYPASSES THE
# FUNCTION ITSELF, SO THERE IS NO RECURSION.
aardvark() {
    if [ "$1" = "cd" ]; then
        local target
        target="$(command aardvark "$@")" || return $?
        [ -n "$target" ] && builtin cd -- "$target"
        return $?
    fi
    command aardvark "$@"
}
av() { aardvark "$@"; }
