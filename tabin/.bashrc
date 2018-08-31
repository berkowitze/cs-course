#
# ~/.bashrc
#
# This is the initialization file for bash, and is read each time an instance of
# your shell executes. A shell starts up, for example, when you open a new xterm
# window, remotely log on to another machine, or type 'bash' or 'sh' to start a
# new shell explicitly.
#
# Refer to bash(1) for more information.
#
# The shell treats lines beginning with # as comments.
#
# EDIT THIS FILE to customize *only* shell-specific options for bash (e.g.
# prompt). All other shell options go in ~/.environment.
#

# Define the shell-independent environment commands. See hooks(7) for more
# information.
setenvvar () { eval $1=\"$2\"; export $1; }
setenvifnot () { if eval [ -z \"\$$1\" ]; then eval $1=\"$2\"; export $1; fi; }
pathappend () { if eval expr ":\$$1::" : ".*:$2:.*" >/dev/null 2>&1; then true; else eval $1=\$$1:$2; fi; }
pathappendifdir () { if [ -d "$2" ]; then pathappend $*; fi; }
pathprepend () { if eval expr ":\$$1::" : ".*:$2:.*" >/dev/null 2>&1; then true; else eval $1=$2:\$$1; fi; }
pathprependifdir () { if [ -d "$2" ]; then pathprepend $*; fi; }
shellcmd () { _cmd=$1; shift; eval "$_cmd () { command $* \"\$@\"; }"; }
sourcefile () { if [ -f "$1" ]; then . $1; fi; }

# Load personal environment settings.
sourcefile $HOME/.environment

# Run the coursehooks.
sourcefile /u/system/hooks/sh/identities
# If this is a non-interactive shell, exit. The rest of this file is loaded
# only for interactive shells.
if [ -z "$PS1" ]; then
	return
fi

# Set tty options.
stty sane

# Set the shell to prevent programs from dumping core.
ulimit -Sc 0

# Set the prompt.
PS1="\[`tput rev`\]\h\[`tput sgr0`\] \w \$ ";

export JAVA_HOME="/course/cs0320/bin/jdk1.8.0_25"
export JDK_HOME=/pro/java/linux/jdk1.8.0
export JRE_HOME=/pro/java/linux/jdk1.8.0
alias javac=/pro/java/linux/jdk1.8.0/bin/javac
alias java=/pro/java/linux/jdk1.8.0/bin/java
export PATH="$PATH:/course/cs0050/www/tidy-html5/build/cmake"

## universal setup
export EDITOR="vim"
export VISUAL="vim"

## terminal setup, end universal setup

# ssh-add if it doesn't exist
alias sl="fortune"
alias rssh="ssh pi@carlson2.local"
alias ocaml="ledit ocaml"

## move up $1 directories
up(){
  local d=""
  limit=$1
  for ((i=1 ; i <= limit ; i++))
    do
      d=$d/..
    done
  d=$(echo $d | sed 's/^\///')
  if [ -z "$d" ]; then
    d=..
  fi
  cd $d
}

## set PS1
RESET="\[\017\]"
NORMAL="\[\033[0m\]"
RED="\[\033[31;1m\]"
YELLOW="\[\033[33;1m\]"
WHITE="\[\033[37;1m\]"
GREEN="\[\033[32;1m\]"
SMILEY="${GREEN}:)${NORMAL}"
FROWNY="${RED}:(${NORMAL}"
SELECT="if [ \$? = 0 ]; then echo \"${SMILEY}\"; else echo \"${FROWNY}\"; fi"

PROMPT_DIRTRIM=2

# Throw it all together 
export PS1="${RESET}${YELLOW}Brown${NORMAL}$SSH_FLAG \`${SELECT}\` \w/${YELLOW}${NORMAL}$ "

## colorize man pages
export LESS_TERMCAP_mb=$'\E[01;31m'
export LESS_TERMCAP_md=$'\E[01;31m'
export LESS_TERMCAP_me=$'\E[0m'
export LESS_TERMCAP_se=$'\E[0m'
export LESS_TERMCAP_so=$'\E[01;44;33m'
export LESS_TERMCAP_ue=$'\E[0m'
export LESS_TERMCAP_us=$'\E[01;32m'
export LESS=-R

## set up history
export HISTFILESIZE=20000
export HISTSIZE=10000

HISTCONTROL=ignoredups
HISTCONTROL=ignoreboth
export HISTIGNORE="&:ls:[bf]g:exit"
export HISTIGNORE="&:??:[ ]*:clear:exit:logout"

## make ls colorful
# ~/.dircolors/themefile

## handy unzipping tool for archives
extract () {
     if [ -f $1 ] ; then
         case $1 in
             *.tar.bz2)   tar xjf $1        ;;
             *.tar.gz)    tar xzf $1        ;;
             *.bz2)       bunzip2 $1        ;;
             *.rar)       rar x $1          ;;
             *.gz)        gunzip $1         ;;
             *.tar)       tar xf $1         ;;
             *.tbz2)      tar xjf $1        ;;
             *.tgz)       tar xzf $1        ;;
             *.zip)       unzip $1          ;;
             *.Z)         uncompress $1     ;;
             *.7z)        7z x $1           ;;
             *)           echo "'$1' cannot be extracted via extract()" ;;
         esac
     else
         echo "'$1' is not a valid file"
     fi
}

# go to previous directory
alias back="cd $OLDPWD"

# list all folders and their sizes
alias folders='find . -maxdepth 1 -type d -print0 | xargs -0 du -sk | sort -rn'

# dynamically update window size
shopt -s checkwinsize

## set ctrl-w to delete last short-word
stty werase undef
bind '\C-w:unix-filename-rubout'

alias cpk="cat $HOME/bin/knight.txt | xclip -selection c"
alias 50="cd /course/cs0050"
alias A="cd /course/cs0111"
alias ck="clear && printf '\e[3J'"
export PATH="$PATH:/course/cs0111/htabin:/course/cs0111/tabin"

alias ta-venv="source /course/cs0050/ta/grading/venv/bin/activate"
export AWEB="/web/cs/web/courses/csci0111"
alias tsuite="cd /home/jswrenn/projects/testing/evaluator"
export PATH=$HOME/.local/bin:$PATH
export npm_config_userconfig=$HOME/.config/npmrc
export PATH=$HOME/.local/bin:$PATH
export npm_config_userconfig=$HOME/.config/npmrc
export PATH=$HOME/.local/bin:$PATH
export npm_config_userconfig=$HOME/.config/npmrc
