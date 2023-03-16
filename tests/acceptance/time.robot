*** Settings ***
Resource       common.resource
Library        DeviceLibrary    adapter=docker
Library        DateTime
Library        String


*** Test Cases ***

Get Test Start Time 1
    ${suite_start}=    Get Suite Start Time
    ${datetime1}=    Get Test Start Time
    Set Suite Variable    ${datetime1}
    Date is Newer    ${suite_start}    ${datetime1}

Get Test Start Time 2
    ${suite_start}=    Get Suite Start Time
    ${datetime2}=    Get Test Start Time
    Set Suite Variable    ${datetime2}
    Date is Newer    ${datetime1}    ${datetime2}
    Date is Newer    ${suite_start}    ${datetime1}

Get Test Start Time 3
    ${suite_start}=    Get Suite Start Time
    ${datetime3}=    Get Test Start Time
    Date is Newer    ${datetime2}    ${datetime3}
    Date is Newer    ${suite_start}    ${datetime1}

Get UnixTimestamp as seconds
    ${value}    Get Unix Timestamp
    Should Be True    ${value} > 0

Get UnixTimestamp with milliseconds
    ${value1}    Get Unix Timestamp
    ${value2}    Get Unix Timestamp    milliseconds=${True}
    Should Be True    ${value2} > ${value1}

*** Keywords ***

Date is Newer
    [Arguments]    ${date1}    ${date2}
    ${diff}=    DateTime.Subtract Date From Date    ${date2}    ${date1}
    Should Be True    ${diff} > 0
