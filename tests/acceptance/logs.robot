*** Settings ***
Resource       common.resource
Library        DeviceLibrary


*** Test Cases ***

Get Device Logs
    [Template]    Get Device Logs
    # local
    ssh
    docker

*** Keywords ***

Get Device Logs
    [Arguments]    ${ADAPTER}
    ${DEVICE_SN}=    Setup    skip_bootstrap=${True}    adapter=${ADAPTER}
    Get Logs
