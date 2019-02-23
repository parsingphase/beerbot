#!/bin/bash

set -e

get_script_dir () {
    SOURCE="${BASH_SOURCE[0]}"
    SOURCE_DIR=$( dirname "$SOURCE" )
    SOURCE_DIR=$(cd -P ${SOURCE_DIR} && pwd)
    echo ${SOURCE_DIR}
}

SCRIPT_DIR="$( get_script_dir )"

try_mac_help() {
   OS=`uname -s`	
   if [[ "$OS" == "Darwin" ]]; then
   echo "It looks like you're on a Mac…"
   which brew > /dev/null || BREW_MISSING="$?"
   if [[ "$BREW_MISSING" == "1" ]]; then
     echo "The easiest way to get python3 and pipenv is probably to install Homebrew - see https://brew.sh"
     echo "You can then set up python and pipenv with 'brew install python3 pipenv'"
   else
     echo "You seem to have homebrew, so you can install python3 and pipenv with 'brew install python3 pipenv'"
   fi
   echo
   fi
}

SCRIPT_DIR="$( get_script_dir )"
cd ${SCRIPT_DIR}

VALID_ENV="1"
echo

which python3 > /dev/null || PYTHON_MISSING="$?"
if [[ "$PYTHON_MISSING" == "1" ]]; then
  echo "Python3 does not appear to be available. See https://realpython.com/installing-python/ for help."
  echo "If you're sure python3 is installed, make sure it's on your path."
  try_mac_help
  exit 1
fi

which pipenv > /dev/null || PIPENV_MISSING="$?"
if [[ "$PIPENV_MISSING" == "1" ]]; then
  echo "pipenv is missing. See https://pipenv.readthedocs.io/en/latest/install/#installing-pipenv for help."
  echo "If you're sure pipenv is installed, make sure it's on your path."
  echo "This is the last thimg you need to install manually to run these scripts."
  try_mac_help
  exit 1
fi

pipenv --venv > /dev/null 2>&1 || ENV_UNBUILT="$?"
if [[ "$ENV_UNBUILT" == "1" ]]; then
  echo "Downloading code required by untappd-tools."
  echo "This only happens once and will not affect the rest of your system." 
  pipenv install
  echo
fi
echo "Entering the project environment. You can now run any of the tools included." 
echo "Try one of the following for help, or check the README:"
echo " ./imbibed.py --help"
echo " ./stock_check.py --help"
echo
echo "Once you're done running the tools, type 'exit' to get back to a normal shell"
echo 
pipenv shell || echo "Sorry, the environment didn't load."
