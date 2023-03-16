*** Settings ***
Resource       common.resource
Library        DeviceLibrary    adapter=docker

Suite Setup    Test Setup


*** Test Cases ***

Start/Stop/Restart
    ${service}=    Set Variable     ssh
    Start Service    ${service}
    Service Should Be Running    ${service}

    Stop Service    ${service}
    Service Should Be Stopped    ${service}

    Enable Service    ${service}
    Service Should Be Enabled    ${service}

    Disable Service    ${service}
    Service Should Be Disabled    ${service}


Reload service manager
    Reload Services Manager

*** Keywords ***

Test Setup
    Setup    skip_bootstrap=${True}
