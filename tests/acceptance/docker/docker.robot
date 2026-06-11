*** Settings ***
Documentation    Integration tests for the single container docker adapter.
...              Requires a running docker daemon. The tests are self-contained
...              and only use public images.
Library          DeviceLibrary    adapter=docker

*** Test Cases ***
Create A Single Container Device
    ${SERIAL}=    Setup    skip_bootstrap=${True}    image=alpine:3.19
    ${output}=    Execute Command    echo device $DEVICE_ID    strip=${True}
    Should Be Equal    ${output}    device ${SERIAL}
    # in single container mode the container is named after the serial number
    ${name}=    Get Container Name
    Should Be Equal    ${name}    ${SERIAL}

Create Multiple Devices In One Suite
    ${DEVICE1}=    Setup    skip_bootstrap=${True}    image=alpine:3.19
    ${DEVICE2}=    Setup    skip_bootstrap=${True}    image=alpine:3.19
    Should Not Be Equal    ${DEVICE1}    ${DEVICE2}
    ${output}=    Execute Command    echo $DEVICE_ID    strip=${True}    device_name=${DEVICE1}
    Should Be Equal    ${output}    ${DEVICE1}
    ${output}=    Execute Command    echo $DEVICE_ID    strip=${True}    device_name=${DEVICE2}
    Should Be Equal    ${output}    ${DEVICE2}
