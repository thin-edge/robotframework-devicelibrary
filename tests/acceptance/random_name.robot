*** Settings ***
Resource       common.resource
Library        DeviceLibrary    adapter=docker

*** Test Cases ***

Get Random Name
    ${name1}=    Get Random Name
    Should Match Regexp    ${name1}    ^TST_[a-zA-Z0-9_]+$

    ${name2}=    Get Random Name
    Should Match Regexp    ${name1}    ^TST_[a-zA-Z0-9_]+$
    Should Not Be Equal    ${name1}    ${name2}

Get Random With Custom Prefix
    ${name2}=    Get Random Name    prefix=DEV
    Should Match Regexp    ${name2}    ^DEV_[a-zA-Z0-9_]+$
