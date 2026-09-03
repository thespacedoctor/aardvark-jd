# PROTOTYPE - wayfinder ticket 07. THROWAWAY.
# setup.sh copies this to env.sh with the paths filled in. Sourced by the
# Script Filter before it runs sf_emoji.py.

export AARDVARK_PY="/Users/dave/anaconda/envs/aardvark-jd/bin/python"
export PROTO_CACHE="/var/folders/bb/nb9yvn71297_6x279rkf_tbm0000gn/T/aardvark-tk07"

# Alfred runs scripts under `/bin/zsh --no-rcs`, so nothing from ~/.zshrc is
# present - including ANTHROPIC_API_KEY. The emoji call needs it. Keep the key
# OUT of this repo: put it in ~/.aardvark-proto-key (chmod 600) and this line
# reads it at run time.
[ -f "$HOME/.aardvark-proto-key" ] && export ANTHROPIC_API_KEY="$(cat "$HOME/.aardvark-proto-key")"
