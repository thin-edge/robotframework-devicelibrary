#!/usr/local/bin/python3
"""Device Library for Robot Framework

It enables the creation of devices which can be used in tests.
It currently support the creation of Docker devices only
"""

import logging
from typing import Any, Dict, List, Union, Optional
from datetime import datetime, timezone
import re
import os
import time
from pathlib import Path

import dotenv
from unidecode import unidecode
from robot.libraries.BuiltIn import BuiltIn
from robot.api.deco import keyword, library
from robot.utils import is_truthy
from device_test_core.adapter import DeviceAdapter

from device_test_core.retry import configure_retry_on_members
from device_test_core.utils import generate_name


def raise_adapter_error(adapter: str):
    """
    Raise an adapter error and hint on what dependency is missing

    Args:
        adapter (str): adapter type, e.g. ssh, docker, local
    """
    raise ValueError(
        f"Missing device adapter '{adapter}'. "
        f"please install robotframework-devicelibrary[{adapter}]"
    ) from None


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
        adapter: Optional[str] = None,
        image: str = DEFAULT_IMAGE,
        bootstrap_script: str = DEFAULT_BOOTSTRAP_SCRIPT,
    ):
        self.devices: Dict[str, DeviceAdapter] = {}
        self.devices_setup_times = {}
        self.__image = image
        self.adapter = adapter
        self.__bootstrap_script = bootstrap_script
        self.current: Optional[DeviceAdapter] = None
        self.test_start_time: Optional[datetime] = None
        self.suite_start_time: Optional[datetime] = None

        # load any settings from dotenv file
        dotenv.load_dotenv(".env")

        # pylint: disable=invalid-name
        self.ROBOT_LIBRARY_LISTENER = self

        # Configure retries
        configure_retry_on_members(self, "^assert_log_contains")
        configure_retry_on_members(self, "^assert_log_not_contains")

    def _get_adapter(self) -> str:
        return (
            self.adapter
            or BuiltIn().get_variable_value(r"${DEVICE_ADAPTER}")
            or self.DEFAULT_ADAPTER
        )

    #
    # Hooks
    #
    def start_suite(self, _data: Any, _result: Any):
        """Hook which is triggered when the suite starts

        Store information about the running of the suite
        such as the time the suite started.

        Args:
            _data (Any): Test case
            _result (Any): Test case results
        """
        self.suite_start_time = datetime.now(tz=timezone.utc)

    def start_test(self, _data: Any, _result: Any):
        """Hook which is triggered when the test starts

        Store information about the running of the test
        such as the time the test started.

        Args:
            _data (Any): Test case
            _result (Any): Test case results
        """
        ts = None
        try:
            # Use device time (to avoid problems with time drift between host and device)
            ts = self.get_unix_timestamp(milliseconds=True)
            logger.info("Set test start time from device")
        except Exception as ex:
            logger.debug("Could not set start time from device. %s", ex)

        if not ts:
            logger.info("Set test start time from host as no device is active")
            ts = self.get_unix_timestamp_from_host(milliseconds=False)

        self.test_start_time = datetime.fromtimestamp(ts, tz=timezone.utc)

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
    def get_test_start_time(self) -> Optional[datetime]:
        """Get the time that the test was started"""
        return self.test_start_time

    @keyword("Get Suite Start Time")
    def get_suite_start_time(self) -> Optional[datetime]:
        """Get the time that the suite was started"""
        return self.suite_start_time

    @keyword("Get Unix Timestamp")
    def get_unix_timestamp(self, milliseconds: bool = False) -> Union[int, float]:
        """Get the unix timestamp of the device (number of seconds since 1970-01-01).
        This returns the unix timestamp of the device under test, not the host where
        the test is being called from.

        When using seconds it will round down (using a cast).

        Args:
            milliseconds (bool, optional): Include milliseconds or not

        Returns:
            Union[int,float]: Number of seconds since unix epoch
        """
        if milliseconds:
            nano_seconds = self.execute_command(
                r"date +%s%N", stdout=True, stderr=False
            )
            # `date` in busybox 1.35.0 in Yocto Kirkstone doesn't support nanoseconds and leaves the
            # nanosecond specifier in the output
            if "%N" not in nano_seconds:
                return float(int(nano_seconds) / 1_000_000_000)

        return int(self.execute_command(r"date +%s", stdout=True, stderr=False))

    @keyword("Get Unix Timestamp From Host")
    def get_unix_timestamp_from_host(
        self, milliseconds: bool = False
    ) -> Union[int, float]:
        """Get the unix timestamp from the test host (not the device) (number of seconds since 1970-01-01)

        When using seconds it will round down (using a cast).

        Args:
            milliseconds (bool, optional): Include milliseconds or not

        Returns:
            Union[int,float]: Number of seconds since unix epoch
        """
        if milliseconds:
            return time.time()
        return int(time.time())

    @keyword("Setup")
    def setup(
        self,
        skip_bootstrap: Optional[bool] = None,
        cleanup: Optional[bool] = None,
        adapter: Optional[str] = None,
        env_file=".env",
        **adaptor_config,
    ) -> str:
        """Create a device to use for testing

        The actual device will depend on the configured adapter
        from the library settings which controls what device
        interface is used, e.g. docker or ssh.

        Args:
            skip_bootstrap (bool, optional): Don't run the bootstrap script. Defaults to None
            cleanup (bool, optional): Should the cleanup be run or not. Defaults to None
            adapter (str, optional): Type of adapter to use, e.g. ssh, docker etc. Defaults to None
            **adaptor_config: Additional configuration that is passed to the adapter. It will override
                any existing settings.

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

        # Allow user to override some of the default settings when calling the setup
        # These values are passed to the adapter config
        if adaptor_config:
            logger.info(
                "Using additional configuration provided as kwargs. %s", adaptor_config
            )
            config = {
                **config,
                **adaptor_config,
            }

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
            docker_device_factory = None
            try:
                from device_test_core.docker.factory import DockerDeviceFactory

                docker_device_factory = DockerDeviceFactory()
            except (ImportError, AttributeError):
                raise_adapter_error(adapter_type)

            device_sn = normalize_container_name(generate_custom_name())

            # Use any env variables which contain a host to ip mapping
            # as it will be added to the docker /etc/hosts list to reduce
            # any problems with external ip addresses
            # Example env variable:
            #   DEVICELIBRARY_HOST_MYDOMAIN="example.mydomain.com=1.2.3.4"
            #
            extra_hosts = {}
            if os.path.exists(env_file):
                env_values = dotenv.dotenv_values(env_file)
                hosts = [
                    key
                    for key in env_values.keys()
                    if key.startswith("DEVICELIBRARY_HOST_")
                ]

                for key in hosts:
                    entry = env_values.get(key)
                    if entry:
                        hostname, _, ip_address = entry.partition("=")
                        hostname = re.sub(r"^\w+://", "", hostname)
                        if hostname and ip_address:
                            extra_hosts[hostname] = ip_address

            if docker_device_factory is None:
                raise Exception(f"Could not import adapter. type={adapter_type}")

            device = docker_device_factory.create_device(
                device_sn,
                image=config.pop("image", self.__image),
                env_file=env_file,
                extra_hosts=extra_hosts,
                **config,
            )
        elif adapter_type == "ssh":
            ssh_device_factory = None
            try:
                from device_test_core.ssh.factory import SSHDeviceFactory

                ssh_device_factory = SSHDeviceFactory()
            except (ImportError, AttributeError):
                raise_adapter_error(adapter_type)

            if ssh_device_factory is None:
                raise Exception(f"Could not import adapter. type={adapter_type}")

            device_sn = generate_custom_name()
            env = {
                "DEVICE_ID": device_sn,
            }
            device = ssh_device_factory.create_device(
                device_sn,
                env_file=env_file,
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
        elif adapter_type == "local":
            local_device_factory = None
            try:
                from device_test_core.local.factory import LocalDeviceFactory

                local_device_factory = LocalDeviceFactory()
            except (ImportError, AttributeError):
                raise_adapter_error(adapter_type)

            device_sn = generate_custom_name()
            env = {
                "DEVICE_ID": device_sn,
            }

            if local_device_factory is None:
                raise Exception(f"Could not import adapter. type={adapter_type}")

            device = local_device_factory.create_device(
                device_sn,
                env_file=env_file,
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

        # Record the time after the device has been setup (but not yet bootstrapped)
        self.devices_setup_times[device_sn] = datetime.fromtimestamp(
            self.get_unix_timestamp(milliseconds=True),
            tz=timezone.utc,
        )

        # Install/Bootstrap device here after the container starts due to
        # install problems when systemd is not running (during the build stage)
        # But it also allows us to possibly customize which version is installed
        # for the test
        if not skip_bootstrap and bootstrap_script:
            device.assert_command(bootstrap_script, log_output=True, shell=True)

        return device_sn

    @keyword("Get Setup Time")
    def get_setup_time(self, name: Optional[str] = None):
        """Get setup time of a device (in the local device time)"""
        device = self.get_device(name)
        return self.devices_setup_times.get(device.get_id())

    @keyword("Set Device Context")
    def set_current(self, name: str):
        """Set the device context which controls the device the other
        keywords send the commands to
        """
        device = self.get_device(name)
        self.current = device

    @keyword("Execute Command")
    def execute_command(
        self,
        cmd: str,
        exp_exit_code: Optional[Union[int, str]] = 0,
        ignore_exit_code: bool = False,
        log_output: bool = True,
        strip: bool = False,
        sudo: Optional[bool] = None,
        stdout: bool = True,
        stderr: bool = False,
        device_name: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Execute a command on the device

        Args:
            exp_exit_code (Union[int,str], optional): Expected return code. Defaults to 0.
                Use '!0' if you want to match against a non-zero exit code.
            ignore_exit_code (bool, optional): Ignore the return code. Defaults to False.
            strip (bool, optional): Strip whitespace from the output. Defaults to False.
            sudo (bool, optional): Run command using sudo. Defaults to None.
            stdout (bool, optional): Include stdout in the response. Defaults to True
            stderr (bool, optional): Include stderr in the response. Defaults to False
            device_name (optional, str): Device

        Returns:
            Any: Result. If stdout and stderr are provided then a tuple of (stdout, stderr) is returned, otherwise
                either stdout or stderr are returned as a string
        """
        ignore_exit_code = is_truthy(ignore_exit_code)
        log_output = is_truthy(log_output)
        strip = is_truthy(strip)
        stdout = is_truthy(stdout)
        stderr = is_truthy(stderr)

        if ignore_exit_code:
            exp_exit_code = None

        if sudo is not None:
            kwargs["sudo"] = is_truthy(sudo)

        device = self.get_device(device_name)
        result = device.assert_command(
            cmd,
            exp_exit_code=exp_exit_code,
            log_output=log_output,
            **kwargs,
        )
        output = []
        if stdout:
            output.append(result.stdout.strip() if strip else result.stdout)
        if stderr:
            output.append(result.stderr.strip() if strip else result.stderr)

        if len(output) == 0:
            return

        if len(output) == 1:
            return output[0]

        return tuple(output)

    @keyword("Get IP Address")
    def get_ipaddress(self, device_name: Optional[str] = None) -> str:
        """Return the ip address of the current device

        Args:
            device_name (optional, str): Device

        Returns:
            str: IP address. An empty string is returned if it does not have an ip address
        """
        return self.get_device(device_name).get_ipaddress() or ""

    @keyword("Disconnect From Network")
    def disconnect_network(self, device_name: Optional[str] = None):
        """Disconnect the device from the network.

        This command only does something if the underlying adapter supports it.

        For example, this is not possible with the SSH adapter.

        Args:
            device_name (optional, str): Device
        """
        self.get_device(device_name).disconnect_network()

    @keyword("Connect To Network")
    def connect_network(self, device_name: Optional[str] = None):
        """Connect device to the network.

        This command only does something if the underlying adapter supports it.
        For example, this is not possible with the SSH adapter.

        Args:
            device_name (optional, str): Device

        """
        self.get_device(device_name).connect_network()

    def teardown(self):
        """Stop and cleanup the device"""
        for name, device in self.devices.items():
            try:
                logger.info("Cleaning up device: %s", name)
                device.cleanup()
            except Exception as ex:
                logger.warning("Error during device cleanup. %s", ex)

    def get_device(self, name: Optional[str] = None) -> DeviceAdapter:
        """Get the current device, or the device with the given name

        Args:
            name (Optional[str], optional): Device name. Defaults to current device if not defined.

        Raises:
            AssertionError: Device not found

        Returns:
            DeviceAdapter: Device
        """
        device = self.current
        if name:
            assert (
                name in self.devices
            ), f"Name not found existing device adapters: {list(self.devices.keys())}"

            device = self.devices.get(name)
        assert device
        return device

    def _get_logs(
        self,
        name: Optional[str] = None,
        date_from: Optional[Union[datetime, float]] = None,
        show=True,
    ):
        """Get device logs

        Args:
            name (str, optional): name. Defaults to current device.
            date_from (Union[datetime, float]: Only include logs starting from a specific datetime
                Accepts either datetime object, or a float (linux timestamp) in seconds.
            show (boolean, optional): Show/Display the log entries

        Returns:
            List[str]: List of log lines

        Raises:
            Exception: Unknown device
        """
        device = self.get_device(name)
        log_output = device.get_logs(since=date_from)

        if show:
            for line in log_output:
                print(line)

        return log_output

    @keyword("Get Logs")
    def get_logs(
        self,
        name: Optional[str] = None,
        date_from: Optional[Union[datetime, float]] = None,
        show=True,
    ):
        """Get device logs

        Args:
            name (str, optional): name. Defaults to current device.
            date_from (Union[datetime, float]: Only include logs starting from a specific datetime
                Accepts either datetime object, or a float (linux timestamp) in seconds.
            show (boolean, optional): Show/Display the log entries

        Returns:
            List[str]: List of log lines

        Raises:
            Exception: Unknown device
        """
        return self._get_logs(name=name, date_from=date_from, show=show)

    @keyword("Logs Should Contain")
    def assert_log_contains(
        self,
        text: Optional[str] = None,
        pattern: Optional[str] = None,
        date_from: Optional[Union[datetime, float]] = None,
        min_matches: int = 1,
        max_matches: Optional[int] = None,
        name: Optional[str] = None,
    ) -> List[str]:
        """Assert that the logs should contain the present of a given text or pattern (regex).

        Examples:

            | Logs Should Contain | text=Executing something |
            | Logs Should Contain | pattern=.*Executing something.* |
            | Logs Should Contain | pattern=.*Executing something.* | min_matches=2 |
            | Logs Should Contain | pattern=.*Executing something.* | date_from="2023-01-01" |

        Args:
            text (str, optional): Assert the present of a static string (case insensitive).
                Each line will be checked to see if it contains the given text.

            pattern (str, optional): Assert that a line should match a given regular expression
                (case insensitive). It must match the entire line.

            min_matches (int, optional): Minimum number of expected line matches (inclusive).
                Defaults to 1. Assertion will be ignored if set to None.

            max_matches (int, optional): Maximum number of expected line matches (inclusive).
                Defaults to None. Assertion will be ignored if set to None.

            date_from (Union[datetime, float], optional): Only include log entires from a given
                datetime/timestamp. As a datetime object or a float (in seconds, e.g. linux timestamp).

            name (str, optional): Name of the device to get the logs from.
                Defaults to current device.

        Returns:
            List[str]: List of matching log entries
        """
        entries = self._get_logs(name=name, date_from=date_from, show=False)

        matches = []
        if text:
            text_lower = text.lower()
            matches = [line for line in entries if text_lower in str(line).lower()]
        elif pattern:
            re_pattern = re.compile(pattern, re.IGNORECASE)
            matches = [line for line in entries if re_pattern.match(line) is not None]
        else:
            raise ValueError(
                "Missing required argument. Either 'text' or 'pattern' must be given"
            )

        if min_matches is not None:
            assert len(matches) >= min_matches, (
                "Total matching log entries is less than expected. "
                f"wanted={min_matches} (min)\n"
                f"got={len(matches)}\n\n"
                f"entries:\n{matches}"
            )

        if max_matches is not None:
            assert len(matches) <= max_matches, (
                "Total matching log entries is greater than expected. "
                f"wanted={min_matches} (max)\n"
                f"got={len(matches)}\n\n"
                f"entries:\n{matches}"
            )

        return matches

    @keyword("Logs Should Not Contain")
    def assert_log_not_contains(
        self,
        text: Optional[str] = None,
        pattern: Optional[str] = None,
        date_from: Optional[Union[datetime, float]] = None,
        name: Optional[str] = None,
    ):
        """Assert that the logs should NOT contain the present of a given text or pattern (regex).

        Examples:

            | Logs Should Not Contain | text=Executing something |
            | Logs Should Not Contain | pattern=.*Executing something.* |
            | Logs Should Not Contain | pattern=.*Executing something.* | date_from="2023-01-01" |

        Args:
            text (str, optional): Assert the present of a static string (case insensitive).
                Each line will be checked to see if it contains the given text.

            pattern (str, optional): Assert that a line should match a given regular expression
                (case insensitive). It must match the entire line.

            date_from (Union[datetime, float], optional): Only include log entires from a given
                datetime/timestamp. As a datetime object or a float (in seconds, e.g. linux timestamp).

            name (str, optional): Name of the device to get the logs from.
                Defaults to current device.
        """
        self.assert_log_contains(
            text=text,
            pattern=pattern,
            name=name,
            date_from=date_from,
            min_matches=0,
            max_matches=0,
        )

    @keyword("Transfer To Device")
    def transfer_to_device(self, src: str, dst: str, device_name: Optional[str] = None):
        """Transfer files to a device

        Examples:

            | Transfer To Device | src=${CURDIR}/myfile.txt | dst=/etc/any/path/newfilename.txt |
            | Transfer To Device | src=${CURDIR}/myfile.txt | dst=/etc/any/path/ |
            | Transfer To Device | src=${CURDIR}/*.txt | dst=/etc/any/path/ |

        Args:
            src (str): Source file, folder or pattern
            dst (str): Destination path to copy to the files to
            device_name (optional, str): Device
        """
        self.get_device(device_name).copy_to(src, dst)

    # ----------------------------------------------------
    # Operation system
    # ----------------------------------------------------
    #
    # APT
    #
    @keyword("Update APT Cache")
    def apt_update(self, device_name: Optional[str] = None) -> str:
        """Update APT package cache

        Args:
            device_name (optional, str): Device

        Returns:
            str: Command output
        """
        return self.get_device(device_name).assert_command("apt-get update").stdout

    @keyword("Install Package Using APT")
    def apt_install(self, *packages: str, device_name: Optional[str] = None):
        """Install a list of packages via APT

        You can specify specify to install the latest available, or use
        a specific version

        Args:
            *packages (str): packages to be installed. Version is optional, but when
                provided it should be in the format of 'mypackage=1.0.0'
            device_name (optional, str): Device

        Returns:
            str: Command output
        """
        return (
            self.get_device(device_name)
            .assert_command("apt-get -y install " + " ".join(packages))
            .stdout
        )

    @keyword("Remove Package Using APT")
    def apt_remove(self, *packages: str, device_name: Optional[str] = None) -> str:
        """Remove a package via APT

        Args:
            device_name (optional, str): Device

        Returns:
            str: Command output
        """
        return (
            self.get_device(device_name)
            .assert_command("apt-get -y remove " + " ".join(packages))
            .stdout
        )

    @keyword("Purge Package Using APT")
    def apt_purge(self, *packages: str, device_name: Optional[str] = None) -> str:
        """Purge a package (and its configuration) using APT

        Args:
            *packages (str): packages to be installed
            device_name (optional, str): Device

        Returns:
            str: Command output
        """
        return (
            self.get_device(device_name)
            .assert_command("apt-get -y remove " + " ".join(packages))
            .stdout
        )

    #
    # Files/folders
    #
    @keyword("Directory Should Be Empty")
    def assert_directory_empty(
        self,
        path: str,
        must_exist: bool = False,
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Check if a directory is empty.

        You can define if the check should fail if the folder does not exist or not.

        Args:
            path (str): Directory path
            must_exist(bool, optional): Fail if the directory does not exist.
                Defaults to False.
            device_name (optional, str): Device
        """
        if must_exist:
            self.get_device(device_name).assert_command(
                f"""
                [ -d '{path}' ] && [ -z "$(ls -A '{path}')" ]
                """.strip(),
                **kwargs,
            )
        else:
            # Don't fail if the folder does not exist, just count the contents
            self.get_device(device_name).assert_command(
                f"""
                [ -z "$(ls -A '{path}' 2>/dev/null || true)" ]
                """.strip(),
                **kwargs,
            )

    @keyword("List Directories in Directory")
    def get_directories_in_directory(
        self,
        path: str,
        must_exist: bool = False,
        device_name: Optional[str] = None,
        **kwargs,
    ) -> List[str]:
        """List the directories in a given directory

        Args:
            path (str): Directory path
            must_exist (bool, optional): Should an error be thrown if the directory
                does not exist. Defaults to False.
            device_name (optional, str): Device

        Returns:
            List[str]: List of directories
        """
        device = self.get_device(device_name)
        if must_exist:
            result = device.assert_command(
                f"find '{path}' -maxdepth 1 -mindepth 1 -type d", **kwargs
            )
        else:
            result = device.assert_command(
                f"find '{path}' -maxdepth 1 -mindepth 1 -type d 2>/dev/null || true",
                **kwargs,
            )

        return result.stdout.splitlines()

    @keyword("Directory Should Not Have Sub Directories")
    def assert_directories_count(
        self,
        path: str,
        must_exist: bool = False,
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Check if directory has no sub directories

        Args:
            path (str): Directory path
            must_exist (bool, optional): Should an error be thrown if the directory
                does not exist. Defaults to False.
            device_name (optional, str): Device
        """
        dirs = self.get_directories_in_directory(
            path, must_exist, device_name=device_name, **kwargs
        )
        assert len(dirs) == 0

    @keyword("Directory Should Not Be Empty")
    def assert_directory_not_empty(
        self, path: str, device_name: Optional[str] = None, **kwargs
    ):
        """Check if a directory is empty

        Args:
            path (str): Directory path
            device_name (optional, str): Device
        """
        self.get_device(device_name).assert_command(
            f"""
            [ -d '{path}' ] && [ -n "$(ls -A '{path}')" ]
        """.strip(),
            **kwargs,
        )

    @keyword("Directory Should Exist")
    def assert_directory(self, path: str, device_name: Optional[str] = None, **kwargs):
        """Check if a directory exists

        Args:
            path (str): Directory path
        """
        self.get_device(device_name).assert_command(f"test -d '{path}'", **kwargs)

    @keyword("Directory Should Not Exist")
    def assert_not_directory(
        self, path: str, device_name: Optional[str] = None, **kwargs
    ):
        """Check if a directory does not exists

        Args:
            path (str): Directory path
            device_name (optional, str): Device
        """
        self.get_device(device_name).assert_command(f"! test -d '{path}'", **kwargs)

    @keyword("File Should Exist")
    def assert_file_exists(
        self, path: str, device_name: Optional[str] = None, **kwargs
    ):
        """Check if a file exists

        Args:
            path (str): File path
            device_name (optional, str): Device
        """
        self.get_device(device_name).assert_command(f"test -f '{path}'", **kwargs)

    @keyword("File Should Not Exist")
    def assert_not_file_exists(
        self, path: str, device_name: Optional[str] = None, **kwargs
    ):
        """Check if a file does not exists

        Args:
            path (str): File path
            device_name (optional, str): Device
        """
        self.get_device(device_name).assert_command(f"! test -f '{path}'", **kwargs)

    @keyword("Symlink Should Exist")
    def assert_symlink_exists(
        self,
        path: str,
        target_exists: bool = True,
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Check if a symlink exists

        Args:
            path (str): Symlink path
            target_exists (bool): Check if the target file/directory exists. Defaults to True
            device_name (optional, str): Device
        """
        device = self.get_device(device_name)
        device.assert_command(f"test -L '{path}'", **kwargs)
        if target_exists:
            device.assert_command(f"test -e '{path}'", **kwargs)

    @keyword("Symlink Should Not Exist")
    def assert_not_symlink_exists(
        self, path: str, device_name: Optional[str] = None, **kwargs
    ):
        """Check if a symlink does not exists

        Args:
            path (str): Symlink path
            device_name (optional, str): Device
        """
        self.get_device(device_name).assert_command(f"! test -L '{path}'", **kwargs)

    @keyword("Path Should Have Permissions")
    def assert_linux_permissions(
        self,
        path: str,
        mode: Optional[str] = None,
        owner_group: Optional[str] = None,
        device_name: Optional[str] = None,
        **kwargs,
    ) -> List[str]:
        """Assert the linux group/ownership and permissions (mode) on a given path

        Examples:

            | Path Should Have Permissions| /etc/myscript.sh | mode=644 |
            | Path Should Have Permissions| /etc/myscript.sh | owner_group=root:root |
            | Path Should Have Permissions| /etc/myscript.sh | mode=755 | owner_group=root:root |

        Args:
            path (str): Path to a file or folder to test against
            mode (str): Mode (as an octal), .eg. 644 or 755 etc. Defaults to None
            owner_group (str): Owner/group in the format of owner:group. Defaults to None
            device_name (optional, str): Device

        Returns:
            List[str]: List of the actual mode and owner/group (e.g. ['644', 'root:root'])
        """
        return self.get_device(device_name).assert_linux_permissions(
            path, mode=mode, owner_group=owner_group, **kwargs
        )

    @keyword("File Checksum Should Be Equal")
    def assert_file_checksum(
        self,
        file: str,
        reference_file: str,
        device_name: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Assert that two files are equal by checking their md5 checksum

        Examples:

        | File Checksum Should Be Equal | file=/etc/tedge/tedge.toml | reference_file=${CURDIR}/tedge-reference.toml |

        Args:
            file (str): path to file on the device
            reference_file (str): path to the local file which will be used to compare
                the checksum against
            device_name (optional, str): Device

        Returns:
            str: checksum of the file on the device
        """
        return self.get_device(device_name).assert_file_checksum(
            file, reference_file, **kwargs
        )

    #
    # Service Control
    #
    @keyword("Start Service")
    def start_service(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Start a service

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        self._control_service(
            "start", name, init_system=init_system, device_name=device_name, **kwargs
        )

    @keyword("Stop Service")
    def stop_service(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Stop a service

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        self._control_service(
            "stop", name, init_system=init_system, device_name=device_name, **kwargs
        )

    @keyword("Service Should Be Enabled")
    def service_enabled(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Assert that the service is enabled (to start on device boot)

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        self._control_service(
            "is-enabled",
            name,
            init_system=init_system,
            device_name=device_name,
            **kwargs,
        )

    @keyword("Enable Service")
    def enable_service(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Enable a service to automatically start on boot device boot

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        self._control_service(
            "enable", name, init_system=init_system, device_name=device_name, **kwargs
        )

    @keyword("Service Should Be Disabled")
    def service_disabled(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Assert that the service is enabled (to start on device boot)

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        self._control_service(
            "is-enabled",
            name,
            exp_exit_code="!0",
            init_system=init_system,
            device_name=device_name,
            **kwargs,
        )

    @keyword("Disable Service")
    def disable_service(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Disable a service so it does not automatically start on boot device boot

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        self._control_service(
            "disable", name, init_system=init_system, device_name=device_name, **kwargs
        )

    @keyword("Service Should Be Running")
    def service_running(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ) -> int:
        """Assert that the service is running and return the process id (PID)

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device

        Returns:
            int: PID of the main service
        """
        self._control_service(
            "is-active",
            name,
            init_system=init_system,
            device_name=device_name,
            **kwargs,
        )
        return self._get_service_pid(
            name, init_system=init_system, device_name=device_name, **kwargs
        )

    @keyword("Service Should Be Stopped")
    def service_stopping(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Assert that the service is stopped

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        self._control_service(
            "is-active",
            name,
            exp_exit_code="!0",
            init_system=init_system,
            device_name=device_name,
            **kwargs,
        )

    @keyword("Restart Service")
    def restart_service(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Restart a service

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        self._control_service(
            "restart", name, init_system=init_system, device_name=device_name, **kwargs
        )

    @keyword("Reload Services Manager")
    def reload_services_manager(
        self, init_system: str = "systemd", device_name: Optional[str] = None, **kwargs
    ):
        """Reload the services manager
        For systemd this would be a systemctl daemon-reload

        Args:
            init_system (optional, str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        if init_system == "systemd":
            return (
                self.get_device(device_name)
                .execute_command("systemctl daemon-reload", **kwargs)
                .stdout
            )

        raise NotImplementedError("Currently only systemd is supported")

    @keyword("Get Service PID")
    def get_service_main_pid(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Get the Main PID of a service

        Args:
            name (str): Name of the service
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device
        """
        return self._get_service_pid(
            name, init_system=init_system, device_name=device_name, **kwargs
        )

    def _control_service(
        self,
        action: str,
        name: str,
        exp_exit_code: Union[int, str] = 0,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Check if a file does not exists

        Args:
            name (str): Name of the service
            exp_exit_code (Union[int,str], optional): Expected exit code. Defaults to 0. Use '!0' if you want
                to match against a non-zero exit code.
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device

        """
        init_system = init_system.lower()

        command = ""
        if init_system == "systemd":
            command = f"systemctl {action.lower()} {name}"
        elif init_system == "sysv":
            raise NotImplementedError("Currently only systemd is supported")

        self.get_device(device_name).assert_command(
            command, exp_exit_code=exp_exit_code, **kwargs
        )

    def _get_service_pid(
        self,
        name: str,
        init_system: str = "systemd",
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Check if a file does not exists

        Args:
            name (str): Name of the service
            exp_exit_code (Union[int,str], optional): Expected exit code. Defaults to 0. Use '!0' if you want
                to match against a non-zero exit code.
            init_system (str): Init. system. Defaults to 'systemd'
            device_name (optional, str): Device

        """
        init_system = init_system.lower()

        if init_system == "systemd":
            command = f"systemctl show --property MainPID --value {name}"
        else:
            raise NotImplementedError("Currently only systemd is supported")

        result = self.get_device(device_name).assert_command(command, **kwargs)
        pid = int(result.stdout.strip())
        return pid

    #
    # Processes
    #
    @keyword("Kill Process")
    def kill_process(
        self,
        pid: int,
        signal: str = "KILL",
        wait: bool = True,
        device_name: Optional[str] = None,
        **kwargs,
    ):
        """Kill a process using a given signal, and by default wait for the process
        to be killed.

        Args:
            pid (int): Process id to be killed
            signal (str): Signal to send. Defaults to 'KILL'
            wait (bool): Wait for the process to be killed. Defaults to True
            device_name (optional, str): Device
        """
        self.execute_command(
            f"kill -{signal} {pid}",
            ignore_exit_code=True,
            device_name=device_name,
            **kwargs,
        )
        if wait:
            self.execute_command(
                f"kill -0 {pid}", exp_exit_code="!0", device_name=device_name, **kwargs
            )

    def _count_processes(self, pattern: str, device_name: Optional[str] = None) -> int:
        result = self.get_device(device_name).execute_command(
            f"""
            pgrep -fa '{pattern}' | grep -v "pgrep -fa" | wc -l
        """.strip()
        )
        count = result.stdout.strip()
        return int(count)

    def _find_processes(self, pattern: str, device_name: Optional[str] = None) -> str:
        result = self.get_device(device_name).execute_command(
            f"""
            pgrep -fa '{pattern}' | grep -v "pgrep -fa"
        """.strip()
        )
        return result.stdout.strip()

    @keyword("Process Should Be Running")
    def assert_process_exists(
        self, pattern: str, device_name: Optional[str] = None, **kwargs
    ):
        """Check if at least 1 process is running given a pattern

        Args:
            pattern (str): Process pattern (passed to pgrep -fa '<pattern>')
            device_name (optional, str): Device
        """
        self.get_device(device_name).assert_command(
            f"""
            pgrep -fa '{pattern}' | grep -v "pgrep -fa"
        """.strip(),
            **kwargs,
        )

    @keyword("Process Should Not Be Running")
    def assert_process_not_exists(
        self, pattern: str, device_name: Optional[str] = None, **kwargs
    ):
        """Check that there are no processes matching a given pattern

        Args:
            pattern (str): Process pattern (passed to pgrep -fa '<pattern>')
            device_name (optional, str): Device
        """
        count = self._count_processes(pattern, device_name=device_name)
        processes = self._find_processes(pattern, device_name=device_name)
        count = len(processes.splitlines())
        assert (
            count == 0
        ), f"No processes should have matched. got {count}\n\n{processes}"

    @keyword("Should Match Processes")
    def assert_process_count(
        self,
        pattern: str,
        minimum: int = 1,
        maximum: Optional[int] = None,
        device_name: Optional[str] = None,
        **kwargs,
    ) -> int:
        """Check how many processes are running which match a given pattern

        Args:
            pattern (str): Process pattern (passed to pgrep -fa '<pattern>')
            minimum (int, optional): Minimum number of matches. Defaults to 1.
            maximum (int, optional): Maximum number of matches. Defaults to None.
            device_name (optional, str): Device

        Returns:
            int: Count of matching processes
        """
        processes = self._find_processes(pattern, device_name=device_name)
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
