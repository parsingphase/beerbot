#!/usr/bin/env bash

set -e

SOURCE_FILES="lambda_function.py stock_check.py imbibed.py utils.py"
AWSREGION="eu-west-1"
LAMBDA_NAME="receiveBeerBotMail"

for arg in "$@"; do
    case ${arg} in
        "--upload")
            DO_UPLOAD=1;;
        "--validate")
            DO_VALIDATE=1;;
        *)
            echo "Invalid argument ${arg}. Valid options are --validate, --upload"
            exit 1
    esac
done

get_script_dir () {
     SOURCE="${BASH_SOURCE[0]}"
     while [[ -h "$SOURCE" ]]; do
          DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
          SOURCE="$( readlink "$SOURCE" )"
          [[ ${SOURCE} != /* ]] && SOURCE="$DIR/$SOURCE"
     done
     $( cd -P "$( dirname "$SOURCE" )" )
     pwd
}

SCRIPT_DIR="$( get_script_dir )"
CACHE_DIR="${SCRIPT_DIR}/cache"
BUILD_DIR="${SCRIPT_DIR}/build"
TMP_DIR=$(mktemp -d)
START_DIR=`pwd`

if [[ "${DO_VALIDATE}" == "1" ]]; then
    echo "Validating source code…"
    set +e
    cd ${SCRIPT_DIR} && eval "./venv/bin/flake8 --ignore E501 ${SOURCE_FILES}"
    VALIDATE_RESULT="$?"
    set -e
    if [[ "$VALIDATE_RESULT" == "0" ]]; then
        echo " … Validation passed"
    else
        echo " … Validation failed; return value = $VALIDATE_RESULT"
        exit 1
    fi
fi

mkdir -p ${BUILD_DIR} ${CACHE_DIR}

echo "Building lambda… "
echo " Working in ${TMP_DIR}"

rm -rf "${BUILD_DIR}/lambda.zip" "${BUILD_DIR}/lambda"

for file in ${SOURCE_FILES}; do
    cp ${file} "${TMP_DIR}"
done

if [[ -e config.py ]]; then
    cp config.py "${TMP_DIR}"
fi

BRANCH="$( git symbolic-ref --short HEAD )"
REVISION="$( git describe --tags HEAD )"
CHANGES=""
set +e # Don't bail on expected return=1
git diff-index --quiet HEAD --
if [[ "$?" == "1" ]]; then
    CHANGES="+"
fi
set -e

GIT_VERSION="version='BeerBot $BRANCH $REVISION$CHANGES'"
echo " Building $GIT_VERSION"
echo  ${GIT_VERSION} > "${TMP_DIR}/bot_version.py"

cd "${TMP_DIR}"
echo " Fetching dependencies"
pip install -t . requests > /dev/null 2>&1
rm -rf tests *.dist-info
zip -r "${BUILD_DIR}/lambda.zip" * -x Pillow\* > /dev/null

echo " Lambda file built at '${BUILD_DIR}/lambda.zip'"
cd "${START_DIR}"

echo " … Build complete"

if [[ "${DO_UPLOAD}" == "1" ]]; then
    echo "Uploading as ${LAMBDA_NAME} to ${AWSREGION}…"
    aws lambda update-function-code --function-name ${LAMBDA_NAME} --region ${AWSREGION} \
        --zip-file "fileb://${BUILD_DIR}/lambda.zip" > /dev/null
    echo " … Upload complete"
fi

echo "All Done"
