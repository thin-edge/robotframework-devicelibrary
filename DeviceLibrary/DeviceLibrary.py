#!/usr/local/bin/python3
"""Device Library for Robot Framework

It enables the creation of devices which can be used in tests.
It currently support the creation of Docker devices only
"""

import logging
from typing import Any, List
from datetime import datetime, timezone
import re
import os
from pathlib import Path

import dotenv
from unidecode import unidecode
from robot.libraries.BuiltIn import BuiltIn
from robot.api.deco import keyword, library
from robot.utils import is_truthy
from device_test_core.adapter import DeviceAdapter
from device_test_core.docker.factory import DockerDeviceFactory
from device_test_core.retry import configure_retry_on_members
from device_test_core.ssh.factory import SSHDeviceFactory
from device_test_core.utils import generate_name


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
)
logger = logging.getLogger(__name__)

__version__ = "0.0.1"
__author__ = "Reuben Miller"


def generate_custom_name(prefix: str = "TST") -> str:
    """Generate a random name"""
    return generate_name(prefix=prefix)


def normalize_container_name(name: str) -> str:
    """Normalize the container name so it conforms
    with the allowed characters

    Accents are converted to the non-accented variant, and
    then any other character not matching [^a-zA-Z0-9_.-] is
    removed.
    """
    name = unidecode(name)
    return re.sub("[^a-zA-Z0-9_.-]", "", name)


@library(scope="SUITE", auto_keywords=False)
class DeviceLibrary:
    """Device Library"""

    ROBOT_LISTENER_API_VERSION = 3

    # Default parameter settings
    DEFAULT_IMAGE = "debian-systemd"

    DEFAULT_BOOTSTRAP_SCRIPT = "./bootstrap.sh"

    # Default adapter type
    DEFAULT_ADAPTER = "docker"

    # Class-internal parameters
    __image = ""
    current = None

    # Constructor
    def __init__(
        self,
        adapter: str = None,
        image: str = DEFAULT_IMAGE,
        bootstrap_script: str = DEFAULT_BOOTSTRAP_SCRIPT,
    ):
        self.devices = {}
        self.__image = image
        self.adapter = adapter
        self.__bootstrap_script = bootstrap_script
        self.current: DeviceAdapter = None
        self.test_start_time = None

        # load any settings from dotenv file
        dotenv.load_dotenv(".env")

        # pylint: disable=invalid-name
        self.ROBOT_LIBRARY_LISTENER = self

    def _get_adapter(self) -> str:
        return self.adapter or BuiltIn().get_variable_value(r"${DEVICE_ADAPTER}") or self.DEFAULT_ADAPTER

    #
    # Hooks
    #
    def start_test(self, _data: Any, _result: Any):
        """Hook which is triggered when the test starts

        Store information about the running of the test
        such as the time the test started.

        Args:
            _data (Any): Test case
            _result (Any): Test case results
        """
        self.test_start_time = datetime.now(tz=timezone.utc)

    def end_suite(self, _data: Any, result: Any):
        """End suite hook which is called by Robot Framework
        when the test suite has finished

        Args:
            _data (Any): Test data
            result (Any): Test details
        """
        logger.info("Suite %s (%s) ending", result.name, result.message)
        self.teardown()
        self.devices.clear()

    def end_test(self, _data: Any, result: Any):
        """End test hook which is called by Robot Framework
        when the test has ended

        Args:
            _data (Any): Test data
            result (Any): Test details
        """
        logger.info("Listener: detected end of test")
        if not result.passed:
            logger.info("Test '%s' failed: %s", result.name, result.message)

    #
    # Keywords / helpers
    #
    @keyword("Get Random Name")
    def get_random_name(self, prefix: str = "TST") -> str:
        """Get random name

        Args:
            prefix (str, optional): Name prefix. Defaults to "TST".

        Returns:
            str: Random name
        """

        return generate_custom_name(prefix)

    @keyword("Get Test Start Time")
    def get_test_start_time(self) -> datetime:
        """Get the time that the test was started"""
        return self.test_start_time

    @keyword("Setup")
    def setup(
        self, skip_bootstrap: bool = None, cleanup: bool = None, adapter: str = None
    ) -> str:
        """Create a device to use for testing

        The actual device will depend on the configured adapter
        from the library settings which controls what device
        interface is used, e.g. docker or ssh.

        Args:
            skip_bootstrap (bool, optional): Don't run the bootstrap script. Defaults to None
            cleanup (bool, optional): Should the cleanup be run or not. Defaults to None
            adapter (str, optional): Type of adapter to use, e.g. ssh, docker etc. Defaults to None

        Returns:
            str: Device serial number
        """
        adapter_type = adapter or self._get_adapter()

        config = (
            BuiltIn().get_variable_value(
                "&{{{}_CONFIG}}".format(adapter_type.upper()), {}
            )
            or {}
        )

        should_cleanup = is_truthy(
            cleanup if cleanup is not None else not config.pop("skip_cleanup", False)
        )

        adapter_default_skip_bootstrap = is_truthy(config.pop("skip_bootstrap", False))
        if skip_bootstrap is None:
            # Read the default value from the configuration (if set)
            # This allows the users to set different behaviour based on each adapter
            skip_bootstrap = adapter_default_skip_bootstrap

        bootstrap_script = config.pop("bootstrap_script", self.__bootstrap_script)

        if adapter_type == "docker":
            device_sn = normalize_container_name(generate_custom_name())

            device = DockerDeviceFactory().create_device(
                device_sn,
                image=config.pop("image", self.__image),
                env_file=".env",
                **config,
            )
        elif adapter_type == "ssh":
            device_sn = generate_custom_name()
            env = {
                "DEVICE_ID": device_sn,
            }
            device = SSHDeviceFactory().create_device(
                device_sn,
                env_file=".env",
                env=env,
                **config,
            )
            if os.path.exists(bootstrap_script):
                # Copy file to device even when not doing bootstrapping to
                # allow the user to manually trigger the bootstrap later
                logger.info("Transferring %s script to device", bootstrap_script)
                device.copy_to(bootstrap_script, ".")
                bootstrap_script = os.path.join(".", Path(bootstrap_script).name)
            else:
                skip_bootstrap = True
        else:
            raise ValueError(
                "Invalid adapter type. Only 'ssh' or 'docker' values are supported"
            )

        # Set if the cleanup should be called or not
        device.should_cleanup = should_cleanup
        self.devices[device_sn] = device
        configure_retry_on_members(device, "^assert_command")
        self.current = device

        # Install/Bootstrap device here after the container starts due to
        # install problems when systemd is not running (during the build stage)
        # But it also allows us to possibly customize which version is installed
        # for the test
        if not skip_bootstrap and bootstrap_script:
            device.assert_command(bootstrap_script, log_output=True, shell=True)

        return device_sn

    @keyword("Set Device Context")
    def set_current(self, name: str):
        """Set the device context which controls the device the other
        keywords send the commands to
        """
        assert (
            name in self.devices
        ), f"Name not found existing device adapters: {list(self.devices.keys())}"
        self.current = self.devices.get(name, self.current)

    @keyword("Execute Command")
    def execute_command(
        self,
        cmd: str,
        exp_exit_code: int = 0,
        ignore_exit_code: bool = False,
        log_output: bool = True,
        strip: bool = False,
        **kwargs,
    ) -> str:
        """Execute a command on the device

        Args:
            exp_exit_code (int, optional): Expected return code. Defaults to 0.
            ignore_exit_code (bool, optional): Ignore the return code. Defaults to False.
            strip (bool, optional): Strip whitespace from the output. Defaults to False.

        Returns:
            str: _description_
        """
        if ignore_exit_code:
            exp_exit_code = None

        output = self.current.assert_command(
            cmd,
            exp_exit_code=exp_exit_code,
            log_output=log_output,
            **kwargs,
        )
        try:
            output_text = output.decode("utf-8")
            if strip:
                return output_text.strip()
            return output_text
        except (UnicodeDecodeError, AttributeError):
            if strip:
                return output.strip()
            return output

    @keyword("Get IP Address")
    def get_ipaddress(self) -> str:
        """Return the ip address of the current device

        Returns:
            str: IP address. An empty string is returned if it does not have an ip address
        """
        return self.current.get_ipaddress() or ""

    @keyword("Disconnect From Network")
    def disconnect_network(self):
        """Disconnect the device from the network.

        This command only does something if the underlying adapter supports it.

        For example, this is not possible with the SSH adapter.
        """
        self.current.disconnect_network()

    @keyword("Connect To Network")
    def connect_network(self):
        """Connect device to the network.

        This command only does something if the underlying adapter supports it.
        For example, this is not possible with the SSH adapter.

        """
        self.current.connect_network()

    def teardown(self):
        """Stop and cleanup the device"""
        for name, device in self.devices.items():
            try:
                logger.info("Cleaning up device: %s", name)
                device.cleanup()
            except Exception as ex:
                logger.warning("Error during device cleanup. %s", ex)

    @keyword("Get Logs")
    def get_logs(self, name: str = None):
        """Get device logs

        Args:
            name (str, optional): name. Defaults to current device.

        Raises:
            Exception: Unknown device
        """
        device = self.current
        if name:
            if name not in self.devices:
                raise Exception(f"Could not find device. {name}")

            device = self.devices.get(name)

        for line in device.get_logs():
            print(line)

    @keyword("Transfer To Device")
    def transfer_to_device(self, src: str, dst: str):
        """Transfer files to a device

        Args:
            src (str): Source file, folder or pattern
            dst (str): Destination path to copy to the files to
        """
        self.current.copy_to(src, dst)

    # ----------------------------------------------------
    # Operation system
    # ----------------------------------------------------
    #
    # APT
    #
    @keyword("Update APT Cache")
    def apt_update(self) -> str:
        """Update APT package cache

        Returns:
            str: Command output
        """
        return self.current.assert_command("apt-get update").decode("utf8")

    @keyword("Install Package Using APT")
    def apt_install(self, *packages: str):
        """Install a list of packages via APT

        You can specify specify to install the latest available, or use
        a specific version

        Args:
            *packages (str): packages to be installed. Version is optional, but when
            provided it should be in the format of 'mypackage=1.0.0'

        Returns:
            str: Command output
        """
        return self.current.assert_command(
            "apt-get -y install " + " ".join(packages)
        ).decode("utf8")

    @keyword("Remove Package Using APT")
    def apt_remove(self, *packages: str) -> str:
        """Remove a package via APT

        Returns:
            str: Command output
        """
        return self.current.assert_command(
            "apt-get -y remove " + " ".join(packages)
        ).decode("utf8")

    @keyword("Purge Package Using APT")
    def apt_purge(self, *packages: str) -> str:
        """Purge a package (and its configuration) using APT

        Args:
            *packages (str): packages to be installed

        Returns:
            str: Command output
        """
        return self.current.assert_command(
            "apt-get -y remove " + " ".join(packages)
        ).decode("utf8")

    #
    # Files/folders
    #
    @keyword("Directory Should Be Empty")
    def assert_directory_empty(self, path: str, must_exist: bool = False):
        """Check if a directory is empty.

        You can define if the check should fail if the folder does not exist or not.

        Args:
            path (str): Directory path
            must_exist(bool, optional): Fail if the directory does not exist.
                Defaults to False.
        """
        if must_exist:
            self.current.assert_command(
                f"""
                [ -d '{path}' ] && [ -z "$(ls -A '{path}')" ]
                """.strip()
            )
        else:
            # Don't fail if the folder does not exist, just count the contents
            self.current.assert_command(
                f"""
                [ -z "$(ls -A '{path}' 2>/dev/null || true)" ]
                """.strip()
            )

    @keyword("List Directories in Directory")
    def get_directories_in_directory(
        self, path: str, must_exist: bool = False
    ) -> List[str]:
        """List the directories in a given directory

        Returns:
            List[str]: List of directories
        """
        if must_exist:
            output = self.current.assert_command(
                f"find '{path}' -maxdepth 1 -mindepth 1 -type d"
            )
        else:
            output = self.current.assert_command(
                f"find '{path}' -maxdepth 1 -mindepth 1 -type d 2>/dev/null || true"
            )

        return output.decode("utf8").splitlines()

    @keyword("Directory Should Not Have Sub Directories")
    def assert_directories_count(self, path: str, must_exist: bool = False):
        """Check if directory has no sub directories

        Args:
            path (str): Directory path
            must_exist (bool, optional): Should an error be thrown if the directory
                does not exist. Defaults to False.
        """
        dirs = self.get_directories_in_directory(path, must_exist)
        assert len(dirs) == 0

    @keyword("Directory Should Not Be Empty")
    def assert_directory_not_empty(self, path: str):
        """Check if a directory is empty

        Args:
            path (str): Directory path
        """
        self.current.assert_command(
            f"""
            [ -d '{path}' ] && [ -n "$(ls -A '{path}')" ]
        """.strip()
        )

    @keyword("Directory Should Exist")
    def assert_directory(self, path: str):
        """Check if a directory exists

        Args:
            path (str): Directory path
        """
        self.current.assert_command(f"test -d '{path}'")

    @keyword("Directory Should Not Exist")
    def assert_not_directory(self, path: str):
        """Check if a directory does not exists

        Args:
            path (str): Directory path
        """
        self.current.assert_command(f"! test -d '{path}'")

    @keyword("File Should Exist")
    def assert_file_exists(self, path: str):
        """Check if a file exists

        Args:
            path (str): File path
        """
        self.current.assert_command(f"test -f '{path}'")

    @keyword("File Should Not Exist")
    def assert_not_file_exists(self, path: str):
        """Check if a file does not exists

        Args:
            path (str): File path
        """
        self.current.assert_command(f"! test -f '{path}'")

    #
    # Service Control
    #
    @keyword("Start Service")
    def start_service(self, name: str, init_system: str = "systemd"):
        """Start a service

        Args:
            path (str): File path
        """
        self._control_service("start", name, init_system=init_system)

    @keyword("Stop Service")
    def stop_service(self, name: str, init_system: str = "systemd"):
        """Stop a service

        Args:
            path (str): File path
        """
        self._control_service("stop", name, init_system=init_system)

    @keyword("Restart Service")
    def restart_service(self, name: str, init_system: str = "systemd"):
        """Restart a service

        Args:
            path (str): File path
        """
        self._control_service("restart", name, init_system=init_system)

    @keyword("Reload Services Manager")
    def reload_services_manager(self, init_system: str = "systemd"):
        """Reload the services manager
        For systemd this would be a systemctl daemon-reload
        """
        if init_system == "systemd":
            return self.execute_command("systemctl daemon-reload")

        raise NotImplementedError("Currently only systemd is supported")

    def _control_service(self, action: str, name: str, init_system: str = "systemd"):
        """Check if a file does not exists

        Args:
            path (str): File path
        """
        init_system = init_system.lower()

        if init_system == "systemd":
            command = f"systemctl {action.lower()} {name}"
        elif init_system == "sysv":
            raise NotImplementedError("Currently only systemd is supported")

        self.current.assert_command(command)

    #
    # Processes
    #
    def _count_processes(self, pattern: str) -> int:
        _, output = self.current.execute_command(
            f"""
            pgrep -fa '{pattern}' | grep -v "pgrep -fa" | wc -l
        """.strip()
        )
        count = output.decode("utf8").strip()
        return int(count)

    def _find_processes(self, pattern: str) -> str:
        _, output = self.current.execute_command(
            f"""
            pgrep -fa '{pattern}' | grep -v "pgrep -fa"
        """.strip()
        )
        return output.decode("utf8").strip()

    @keyword("Process Should Be Running")
    def assert_process_exists(self, pattern: str):
        """Check if at least 1 process is running given a pattern

        Args:
            pattern (str): Process pattern (passed to pgrep -fa '<pattern>')
        """
        self.current.assert_command(
            f"""
            pgrep -fa '{pattern}' | grep -v "pgrep -fa"
        """.strip()
        )

    @keyword("Process Should Not Be Running")
    def assert_process_not_exists(self, pattern: str):
        """Check that there are no processes matching a given pattern

        Args:
            pattern (str): Process pattern (passed to pgrep -fa '<pattern>')
        """
        count = self._count_processes(pattern)
        processes = self._find_processes(pattern)
        count = len(processes.splitlines())
        assert (
            count == 0
        ), f"No processes should have matched. got {count}\n\n{processes}"

    @keyword("Should Match Processes")
    def assert_process_count(
        self, pattern: str, minimum: int = 1, maximum: int = None
    ) -> int:
        """Check how many processes are running which match a given pattern

        Args:
            pattern (str): Process pattern (passed to pgrep -fa '<pattern>')
            minimum (int, optional): Minimum number of matches. Defaults to 1.
            maximum (int, optional): Maximum number of matches. Defaults to None.

        Returns:
            int: Count of matching processes
        """
        processes = self._find_processes(pattern)
        count = len(processes.splitlines())
        if minimum is not None:
            assert (
                count >= minimum
            ), f"Expected process count to be greater than or equal to {minimum}, got {count}\n\n{processes}"

        if maximum is not None:
            assert (
                count <= maximum
            ), f"Expected process count to be less than or equal to {maximum}, got {count}\n\n{processes}"

        return count


if __name__ == "__main__":
    pass
