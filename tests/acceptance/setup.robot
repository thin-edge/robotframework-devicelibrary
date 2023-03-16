*** Settings ***
Resource       common.resource
Library        DeviceLibrary


*** Test Cases ***

Start up a device
    [Template]    Start up a device
    local
    ssh
    docker

*** Keywords ***

Start up a device
    [Arguments]    ${ADAPTER}
    ${DEVICE_SN}=    Setup                 skip_bootstrap=True    adapter=${ADAPTER}
    Should Not Be Empty    ${DEVICE_SN}
