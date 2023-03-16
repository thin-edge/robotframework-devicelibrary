*** Settings ***
Resource       common.resource
Library        DeviceLibrary    adapter=docker

Suite Setup    Test Setup


*** Test Cases ***

Kill process
    Process Should Be Running    ${name}
    ${pid}=    Execute Command    pgrep -fa ${name} | cut -d' ' -f1 | head -n 1    strip=${True}    stderr=${False}
    Kill Process    ${pid}
    Process Should Not Be Running    ${name}
    ${count}=    Should Match Processes    ${name}    minimum=0    maximum=0

*** Keywords ***

Test Setup
    Setup    skip_bootstrap=${True}
    Transfer To Device    ${CURDIR}/services/helloworld.service    /etc/systemd/system/
    Set Suite Variable    $name    helloworld

    Reload Services Manager
    Start Service    ${name}
    Service Should Be Running    ${name}

Test Cleanup
    Stop Service    ${name}
    Execute Command    rm -f /etc/systemd/system/helloworld.service
    Reload Services Manager
