*** Settings ***
Resource       common.resource
Library        DeviceLibrary


*** Test Cases ***

Package lifecycle
    [Template]    Package lifecycle
    # local
    ssh
    docker


*** Keywords ***

Package lifecycle
    [Arguments]    ${ADAPTER}
    ${DEVICE_SN}=    Setup    skip_bootstrap=${True}    adapter=${ADAPTER}
    Update APT Cache
    Install Package Using APT    jq
    Execute Command    jq --version
    Remove Package Using APT    jq
    Purge Package Using APT    jq
    Execute Command    jq    exp_exit_code=!0
