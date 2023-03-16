*** Settings ***
Resource       common.resource
Library        DeviceLibrary

Suite Setup    Test Setup
Test Teardown    Test Cleanup


*** Test Cases ***

Empty directory
    Execute Command    mkdir -p /tmp/empty/
    Directory Should Be Empty    /tmp/empty

    Execute Command    touch /tmp/empty/foo
    Directory Should Not Be Empty    /tmp/empty


Directory contents
    Execute Command    mkdir -p /tmp/test/dir_contents/
    Directory Should Exist    /tmp/test/dir_contents/
    Directory Should Not Have Sub Directories    /tmp/test/dir_contents/

    Execute Command    mkdir -p /tmp/test/dir_contents/foo
    Execute Command    mkdir -p /tmp/test/dir_contents/bar
    ${dirs}=    List Directories in Directory    /tmp/test/dir_contents/    must_exist=${True}
    Should Contain    ${dirs}    /tmp/test/dir_contents/foo
    Should Contain    ${dirs}    /tmp/test/dir_contents/bar


Directory existence
    Execute Command    mkdir -p /tmp/test/dir_existence/
    Directory Should Exist    /tmp/test/dir_existence/
    Execute Command    rm -rf /tmp/test/dir_existence/
    Directory Should Not Exist    /tmp/test/dir_existence/


File existence
    Execute Command    mkdir -p /tmp/test/file_existence/
    File Should Not Exist    /tmp/test/file_existence/foo
    Execute Command    touch /tmp/test/file_existence/foo
    File Should Exist    /tmp/test/file_existence/foo

*** Keywords ***

Test Setup
    Setup    skip_bootstrap=${True}
    Execute Command    rm -rf /tmp/test
    
Test Cleanup
    Execute Command    rm -rf /tmp/test
