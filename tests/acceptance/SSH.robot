*** Settings ***
Resource       common.resource
Library        DeviceLibrary    adapter=ssh


*** Test Cases ***
Start up a device using ssh
    Setup Device                 skip_bootstrap=True
    Execute Command On Device    ls -la /etc/\
    Process Should Be Running On Device    ssh
    Should Match Processes on Device    /usr/sbin/ssh    minimum=1    maximum=1
