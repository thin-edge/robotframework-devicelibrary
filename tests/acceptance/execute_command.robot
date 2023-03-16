*** Settings ***
Resource       common.resource
Library        DeviceLibrary


*** Test Cases ***

Returns only stdout
    [Template]    Returns only stdout
    local
    ssh
    docker

Returns only stderr
    [Template]    Returns only stderr
    local
    ssh
    docker

Returns both stdout and stderr
    [Template]    Returns both stdout and stderr
    local
    ssh
    docker

*** Keywords ***

Returns only stderr
    [Arguments]    ${ADAPTER}
    Setup                 skip_bootstrap=True    adapter=${ADAPTER}
    ${stderr}=    Execute Command    ls -la . >&2        stdout=${False}    stderr=${True}    sudo=${False}
    Should Not Be Empty    ${stderr}

Returns only stdout
    [Arguments]    ${ADAPTER}
    Setup                 skip_bootstrap=True    adapter=${ADAPTER}
    ${stdout}=    Execute Command    ls -la .        stdout=True    stderr=False    sudo=${False}
    Should Not Be Empty    ${stdout}

Returns both stdout and stderr
    [Arguments]    ${ADAPTER}
    Setup                 skip_bootstrap=True    adapter=${ADAPTER}
    ${stdout}    ${stderr}=    Execute Command    echo "hello"; echo "world" >&2        stdout=${True}    stderr=${True}    sudo=${False}
    Should Be Equal    ${stdout}    hello${\n}
    Should Be Equal    ${stderr}    world${\n}
