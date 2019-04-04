#!/usr/bin/env bash
set -e -u -x -o pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
XCODE_CONFIGURATION_BUILD_DIR=${PWD}/iostestbuild

USAGE="USAGE: xcodeunittests.sh <projectfile> <xcodescheme> <appname> <logdir> <testname> <device> <os> <opt:--extra-args xcode_extra_args> <opt:--usegui>"
PROJECT="${1?$USAGE}"  # Xcode project file
SCHEME="${2?$USAGE}"  # Xcode scheme name
APPNAME="${3?$USAGE}"  # name of the app (without .app extension)
LOGDIR="${4?$USAGE}"  # path to the directory to store logs in
TESTNAME="${5?$USAGE}"  # name of the kind of test (unittest/quickstart) to use for naming the logfile
DEVICE="${6?$USAGE}"  # device name to test on
OS="${7?$USAGE}"  # os to test with
shift 7

xcodeExtraArgs=()
USEGUI=
while [[ $# > 0 ]]
do
    key="$1"
    case $key in
    --extra-args)
        [[ -n $2 ]] ||
            exitWithError "Error: expected argument for %s option\n" "$key"
        xcodeExtraArgs+=("$2")
        shift
        ;;
    --usegui)
        USEGUI=1
        ;;
    *)
        exitWithError "Error: unrecognized option '%s'\n" "$key"
        ;;
    esac
shift # past argument or value
done

run_test() {
    local thistestname simname uid

    cleanup() {
        local simname
        simname=$1
        ${SCRIPT_DIR}/ios_simulator_cli.sh ${simname} shutdown || true
        if [[ ${USEGUI} ]]; then
            osascript -e 'quit app "Simulator"'
        fi
    }
    simname="${DEVICE}-${OS}"
    trap "cleanup $simname" EXIT
    thistestname="$TESTNAME-$simname"

    if [[ ! -d ${LOGDIR} ]]; then
        echo "logging directory does not exist"
        exit
    fi
    ${SCRIPT_DIR}/ios_simulator_cli.sh ${simname} create "${DEVICE}" "${OS}"
    uid=$(${SCRIPT_DIR}/ios_simulator_cli.sh ${simname} getuid)

    if [[ -n ${USEGUI} ]]; then
        ${SCRIPT_DIR}/ios_simulator_cli.sh ${simname} open
    else
        ${SCRIPT_DIR}/ios_simulator_cli.sh ${simname} boot
    fi

    rm -rf ${XCODE_CONFIGURATION_BUILD_DIR}

    xcodebuild build-for-testing -project ${PROJECT} \
        -destination "platform=iOS Simulator,id=${uid}" \
        -scheme ${SCHEME} ${xcodeExtraArgs[@]} \
        CONFIGURATION_BUILD_DIR=${XCODE_CONFIGURATION_BUILD_DIR} \
        SUBSCRIPTION_KEY="$SPEECHSDK_SPEECH_KEY" SERVICE_REGION="$SPEECHSDK_SPEECH_REGION" 2>&1 |
          tee "${LOGDIR}/xcodebuild-ios-build-${thistestname}.log" |
          xcpretty --report junit --output test-ios-build-${thistestname}.xml

    ${SCRIPT_DIR}/ios_simulator_cli.sh ${simname} wait
    xcrun simctl install ${uid} ${XCODE_CONFIGURATION_BUILD_DIR}/${APPNAME}.app/

    xcodebuild test-without-building -project ${PROJECT} ${xcodeExtraArgs[@]} \
        -destination "platform=iOS Simulator,id=${uid}" \
        -scheme ${SCHEME} \
        CONFIGURATION_BUILD_DIR=${XCODE_CONFIGURATION_BUILD_DIR} \
        SUBSCRIPTION_KEY="$SPEECHSDK_SPEECH_KEY" SERVICE_REGION="$SPEECHSDK_SPEECH_REGION" 2>&1 |
          tee "${LOGDIR}/xcodebuild-ios-run-${thistestname}.log" |
          xcpretty --report junit --output test-ios-run-${thistestname}.xml
}

run_test
