# robotframework-devicelibrary

Robot Framework Library for creating and interacting with devices using various adapters such as ssh, docker and local devices using the same interface.

# Using it

1. Install via pip

    ```sh
    pip install robotframework-devicelibrary[all]  git+https://github.com/reubenmiller/robotframework-devicelibrary.git@0.24.4
    ```

    Or add it to your `requirements.txt` file

    ```sh
    robotframework-devicelibrary[all] @ git+https://github.com/reubenmiller/robotframework-devicelibrary.git@0.24.4
    ```

    Then install it via

    ```sh
    pip install -r requirements.txt
    ```

2. Create a `.env` file with the following environment variables (which will be the secrets)

    ```sh
    # SSH config (which device should be tested when using ssh)
    SSH_CONFIG_HOSTNAME=
    SSH_CONFIG_USERNAME=
    SSH_CONFIG_PASSWORD=
    ```

3. Create a common resource which contains your settings `tests/common.resource`

    ```robot
    ${DEVICE_ADAPTER}    docker
    &{SSH_CONFIG}        hostname=%{SSH_CONFIG_HOSTNAME= }    username=%{SSH_CONFIG_USERNAME= }    password=%{SSH_CONFIG_PASSWORD= }
    &{DOCKER_CONFIG}     image=%{DOCKER_CONFIG_IMAGE=debian-systemd}
    ```

    **Note**

    The common resource references the secrets stored in the .env file so secrets can be kept out of the repository.

4. Create a Robot test `tests/Example.robot`

    ```robot
    *** Settings ***
    Resource       common.resource
    Library        DeviceLibrary    adapter=ssh

    *** Test Cases ***
    Check command execution
        Setup Device
        Execute Command On Device    ls -la /etc/
        Process Should Be Running On Device    ssh
    ```

5. Run the test

    ```sh
    robot tests/Example.robot
    ```

## Docker Compose setups

If a test setup needs more than a single container (e.g. a device plus a broker or other supporting services), pass a docker compose file to the `Setup` keyword and the whole stack will be created:

```robot
*** Settings ***
Library        DeviceLibrary    adapter=docker

*** Test Cases ***
Device with supporting services
    ${SERIAL}=    Setup    compose_file=${CURDIR}/docker-compose.yaml

    # commands run on the main device under test by default
    Execute Command    tedge connect c8y

    # but every service of the stack is addressable via <serial>:<service>
    Execute Command    mosquitto_sub -t 'te/#' -C 1    device_name=${SERIAL}:broker

    # resolve the dynamically assigned host port of a published container port
    ${HOST}    ${PORT}=    Get Service Port    service=broker    port=1883

    # container logs of supporting (non systemd) services
    ${lines}=    Get Service Logs    service=broker

    # simulate a network outage of the device only (the rest of the stack stays up)
    Disconnect From Network
    Connect To Network
```

With an example compose file. The label marks which service acts as the main device under test (alternatively pass `device_service=<name>` to `Setup`, or name the service `device`):

```yaml
services:
  device:
    image: debian-systemd
    labels:
      device-test-core.role: main
  broker:
    image: eclipse-mosquitto:2
    ports:
      - "1883"
```

Each `Setup` creates the stack under a unique compose project name, so all containers, networks and volumes are isolated per test setup and suites can run in parallel. To keep it that way, the compose file must not use `container_name`, fixed host ports (e.g. `8080:80`, use ephemeral ports like `"80"` plus the `Get Service Port` keyword instead), or external/fixed-name networks and volumes. The compose file is validated and the setup is rejected with an explanatory error if it contains such settings.

The `compose_file` and `device_service` settings can also be provided via the `&{DOCKER_CONFIG}` variable instead of keyword arguments.

## Development

The project uses [just](https://github.com/casey/just) to run the common development tasks.

```sh
# Create the python virtual environment (editable install with all adapters)
just venv

# Run the tests (local, ssh, docker and docker compose adapters)
just build-test-images
just start-ssh-device
SSH_CONFIG_HOSTNAME=127.0.0.1 SSH_CONFIG_PORT=2222 SSH_CONFIG_USERNAME=root SSH_CONFIG_PASSWORD=inttest just test
just stop-ssh-device
```

**Notes**

* You can also run a subset of the tests by passing additional robot arguments, e.g. `just test --suite compose` only runs the docker compose tests (which don't need the test image or the ssh device).
* The tests use the `debian-systemd` image built by `just build-test-images`. The same image is started by `just start-ssh-device` and used as the target device for the ssh adapter tests.
* The `local` adapter tests execute commands on your own machine using sudo, so they require passwordless sudo (as is the case on the GitHub Actions runners). Without it those tests will fail locally.

The same tests are run on every push/pull request by the [test workflow](.github/workflows/test.yml).

## Library docs

Checkout the [DeviceLibrary docs](./docs/DeviceLibrary.rst)

You can generate the docs yourself using:

```sh
libdoc DeviceLibrary/DeviceLibrary.py show > docs/DeviceLibrary.rst
```

Or you can create the html docs using:

```sh
libdoc ./DeviceLibrary/DeviceLibrary.py docs/DeviceLibrary.html
```

Then open the [docs/DeviceLibrary.html](docs/DeviceLibrary.html) file in your local web browser.
