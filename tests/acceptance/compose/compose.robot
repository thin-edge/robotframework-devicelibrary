*** Settings ***
Documentation    Integration tests for the docker compose support.
...              Requires a running docker daemon with the compose v2 plugin.
Library          DeviceLibrary    adapter=docker

*** Test Cases ***
Create A Stack From A Compose File
    ${SERIAL}=    Setup    skip_bootstrap=${True}    compose_file=${CURDIR}/docker-compose.yaml
    # main device (labelled with device-test-core.role: main) answers by default
    ${output}=    Execute Command    echo device says $DEVICE_ID    strip=${True}
    Should Be Equal    ${output}    device says ${SERIAL}
    # sidecar services are addressable via <serial>:<service>
    ${output}=    Execute Command    hostname    strip=${True}    device_name=${SERIAL}:helper
    Should Not Be Empty    ${output}
    # services reach each other via service names on the isolated project network
    Execute Command    nc -z -w 5 web 80
    # ephemeral published ports can be resolved to the assigned host port
    ${HOST}    ${PORT}=    Get Service Port    service=web    port=80
    Should Not Be Empty    ${HOST}
    Should Be True    ${PORT} > 0
    # container logs of supporting (non systemd) services
    ${lines}=    Get Service Logs    service=web    show=${False}
    Should Not Be Empty    ${lines}

Simulate Network Outage Of The Device Only
    ${SERIAL}=    Setup    skip_bootstrap=${True}    compose_file=${CURDIR}/docker-compose.yaml
    Disconnect From Network
    Execute Command    nc -z -w 2 web 80    exp_exit_code=!0
    # the rest of the stack is unaffected
    Execute Command    nc -z -w 5 web 80    device_name=${SERIAL}:helper
    Connect To Network
    Execute Command    nc -z -w 5 web 80

Use A Different Service As The Main Device
    ${SERIAL}=    Setup    skip_bootstrap=${True}    compose_file=${CURDIR}/docker-compose.yaml    device_service=helper
    ${output}=    Execute Command    echo i am the helper    strip=${True}
    Should Be Equal    ${output}    i am the helper
    ${output}=    Execute Command    echo i am the device    strip=${True}    device_name=${SERIAL}:device
    Should Be Equal    ${output}    i am the device
