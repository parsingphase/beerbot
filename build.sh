#!/usr/bin/env bash

set -e

get_script_dir () {
     SOURCE="${BASH_SOURCE[0]}"
     while [ -h "$SOURCE" ]; do
          DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
          SOURCE="$( readlink "$SOURCE" )"
          [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
     done
     $( cd -P "$( dirname "$SOURCE" )" )
     pwd
}

SCRIPT_DIR="$( get_script_dir )"
CACHE_DIR="${SCRIPT_DIR}/cache"
BUILD_DIR="${SCRIPT_DIR}/build"
TMP_DIR=$(mktemp -d)
START_DIR=`pwd`

mkdir -p $BUILD_DIR $CACHE_DIR

echo "Building lambda… "

echo "Working in ${TMP_DIR}"

rm -rf "${BUILD_DIR}/lambda.zip" "${BUILD_DIR}/lambda"

cp lambda.py "${TMP_DIR}/lambda_function.py"
cp stock_check.py "${TMP_DIR}"
cp imbibed.py "${TMP_DIR}"
cp utils.py "${TMP_DIR}"

if [[ -e config.py ]]; then
    cp config.py "${TMP_DIR}"
fi

BRANCH="$( git symbolic-ref --short HEAD )"
REVISION="$( git rev-parse --short HEAD )"
CHANGES=""
set +e # Don't bail on expected return=1
git diff-index --quiet HEAD --
if [[ "$?" == "1" ]]; then
    CHANGES="+"
fi
set -e

echo "version='BeerBot $BRANCH #$REVISION$CHANGES'" > "${TMP_DIR}/bot_version.py"

cd "${TMP_DIR}"
pip install -t . requests
rm -rf tests *.dist-info
zip -r "${BUILD_DIR}/lambda.zip" * -x Pillow\* > /dev/null

echo "Lambda file at '${BUILD_DIR}/lambda.zip' updated"
cd "${START_DIR}"

echo "… Done"

if [[ "$1" == "--upload" ]]; then
    AWSREGION="eu-west-1"
    aws lambda update-function-code --function-name receiveBeerBotMail --region "$AWSREGION" --zip-file "fileb://${BUILD_DIR}/lambda.zip"
fi