*** Settings ***
Resource       ../common.resource
Library        DeviceLibrary    adapter=docker

Test Setup    Setup    skip_bootstrap=True

*** Test Cases ***

Disconnect then connect to network
    Execute Command    timeout 12 curl google.com

    Disconnect From Network
    Execute Command    timeout 12 curl google.com    exp_exit_code=!0

    Connect To Network
    Execute Command    timeout 12 curl google.com

*** Keywords ***

