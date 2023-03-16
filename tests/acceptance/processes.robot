*** Settings ***
Resource       common.resource
Library        DeviceLibrary    adapter=docker

Suite Setup    Test Setup


*** Test Cases ***

Process counts
    ${service}=    Set Variable     ssh
    Start Service    ${service}
    Process Should Be Running    ${service}
    
    ${count}=    Should Match Processes    ${service}    minimum=1    maximum=1
    Should Be Equal    ${count}    ${1}

    Stop Service    ${service}
    ${count}=    Should Match Processes    ${service}    minimum=0    maximum=0
    Should Be Equal    ${count}    ${0}

*** Keywords ***

Test Setup
    Setup    skip_bootstrap=${True}
