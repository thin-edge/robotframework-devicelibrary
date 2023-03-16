*** Settings ***
Resource       ../common.resource
Library        DeviceLibrary

*** Test Cases ***

Transfer single file
    [Template]    Transfer single file
    ssh    /test/transfer_to_device/single/
    docker    /test/transfer_to_device/single/
    # Local has problems due to lack of sudo rights
    # local    ${TEMPDIR}/test/transfer_to_device/single/

Transfer multiple files
    [Template]    Transfer multiple files
    ssh    /test/transfer_to_device/multiple
    docker    /test/transfer_to_device/multiple
    # Local has problems due to lack of sudo rights
    # local    ${TEMPDIR}/test/transfer_to_device/multiple/

Transfer folder
    [Template]    Transfer Folder
    ssh    /test/transfer_to_device/folder/
    docker    /test/transfer_to_device/folder/
    # Local has problems due to lack of sudo rights
    # local    ${TEMPDIR}/test/transfer_to_device/folder/

*** Keywords ***

Custom Setup
    Setup    skip_bootstrap=${True}    adapter=docker

Transfer single file
    [Arguments]    ${ADAPTER}    ${DESTINATION}
    Setup    skip_bootstrap=${True}    adapter=${ADAPTER}
    Transfer To Device    ${CURDIR}/data/file1.txt    ${DESTINATION}
    File Should Exist    ${DESTINATION}file1.txt
    Execute Command    rm -rf "${DESTINATION}"

Transfer multiple files
    [Arguments]    ${ADAPTER}    ${DESTINATION}
    Setup    skip_bootstrap=${True}    adapter=${ADAPTER}
    Transfer To Device    ${CURDIR}/data/file*.txt    ${DESTINATION}
    File Should Exist    ${DESTINATION}/file1.txt
    File Should Exist    ${DESTINATION}/file2.txt
    Execute Command    rm -rf "${DESTINATION}"

Transfer folder
    [Arguments]    ${ADAPTER}    ${DESTINATION}
    Setup    skip_bootstrap=${True}    adapter=${ADAPTER}
    Transfer To Device    ${CURDIR}/data    ${DESTINATION}
    File Should Exist    ${DESTINATION}data/file1.txt
    File Should Exist    ${DESTINATION}data/file2.txt
    Execute Command    rm -rf "${DESTINATION}"
