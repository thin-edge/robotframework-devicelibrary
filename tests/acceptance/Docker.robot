*** Settings ***
Resource       common.resource
Library        DeviceLibrary    adapter=docker


*** Test Cases ***
Start up a device using docker
    Setup Device                 skip_bootstrap=True
    Execute Command On Device    ls -la /etc/
