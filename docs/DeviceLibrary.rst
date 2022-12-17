DeviceLibrary
=============
Scope:    GLOBAL

Device Library

Importing
---------
Arguments:  [image: str = debian-systemd, adapter: str = docker]

Initialize self.  See help(type(self)) for accurate signature.

Directory Should Be Empty On Device
-----------------------------------
Arguments:  [path: str]

Check if a directory is empty

Args:
    path (str): Directory path

Directory Should Exist on Device
--------------------------------
Arguments:  [path: str]

Check if a directory exists

Args:
    path (str): Directory path

Directory Should Not Be Empty On Device
---------------------------------------
Arguments:  [path: str]

Check if a directory is empty

Args:
    path (str): Directory path

Directory Should Not Exist on Device
------------------------------------
Arguments:  [path: str]

Check if a directory does not exists

Args:
    path (str): Directory path

Execute Command On Device
-------------------------
Arguments:  [cmd: str, exp_exit_code: int = 0, log_output: bool = True]

Execute a device command

Args:
    exp_exit_code (int, optional): Expected return code. Defaults to 0.

Returns:
    str: _description_

File Should Exist on Device
---------------------------
Arguments:  [path: str]

Check if a file exists

Args:
    path (str): File path

File Should Not Exist on Device
-------------------------------
Arguments:  [path: str]

Check if a file does not exists

Args:
    path (str): File path

Get Device Logs
---------------
Arguments:  [name: str | None = None]

Get device log

Args:
    name (str, optional): name. Defaults to current device.

Raises:
    Exception: Unknown device

Get Random Name
---------------
Arguments:  [prefix: str = STC]

Get random name

Args:
    prefix (str, optional): Name prefix. Defaults to "STC".

Returns:
    str: Random name

Install Package Using APT
-------------------------
Arguments:  [*packages: str]

Install a list of packages via APT

You can specify specify to install the latest available, or use
a specific version

Args:
    *packages (str): packages to be installed. Version is optional, but when
    provided it should be in the format of 'mypackage=1.0.0'

Returns:
    str: Command output

Process Should Be Running On Device
-----------------------------------
Arguments:  [pattern: str]

Check if at least 1 process is running given a pattern

Args:
    pattern (str): Process pattern (passed to pgrep -fa '<pattern>')

Process Should Not Be Running On Device
---------------------------------------
Arguments:  [pattern: str]

Check that there are no processes matching a given pattern

Args:
    pattern (str): Process pattern (passed to pgrep -fa '<pattern>')

Purge Package Using APT
-----------------------
Arguments:  [*packages: str]

Purge a package (and its configuration) using APT

Args:
    *packages (str): packages to be installed

Returns:
    str: Command output

Reload Services Manager
-----------------------
Arguments:  [init_system: str = systemd]

Reload the services manager
For systemd this would be a systemctl daemon-reload

Remove Package Using APT
------------------------
Arguments:  [*packages: str]

Remove a package via APT

Returns:
    str: Command output

Restart Service
---------------
Arguments:  [name: str, init_system: str = systemd]

Restart a service

Args:
    path (str): File path

Setup Device
------------
Arguments:  [skip_bootstrap: bool = False]

Create a container device to use for testing

Returns:
    str: Device serial number

Should Match Processes on Device
--------------------------------
Arguments:  [pattern: str, minimum: int = 1, maximum: int | None = None]

Check how many processes are running which match a given pattern

Args:
    pattern (str): Process pattern (passed to pgrep -fa '<pattern>')
    minimum (int, optional): Minimum number of matches. Defaults to 1.
    maximum (int, optional): Maximum number of matches. Defaults to None.

Returns:
    int: Count of matching processes

Start Service
-------------
Arguments:  [name: str, init_system: str = systemd]

Start a service

Args:
    path (str): File path

Stop Device
-----------
Arguments:  []

Stop and cleanup the device

Stop Service
------------
Arguments:  [name: str, init_system: str = systemd]

Stop a service

Args:
    path (str): File path

Transfer To Device
------------------
Arguments:  [src: str, dst: str]

Transfer files to a device

Args:
    src (str): Source file, folder or pattern
    dst (str): Destination path to copy to the files to

Update APT Cache
----------------
Arguments:  []

Update APT package cache

Returns:
    str: Command output

Wait For Device To Be Ready
---------------------------
Arguments:  []

Wait for the device to be ready

