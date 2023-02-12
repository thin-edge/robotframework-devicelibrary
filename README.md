# robotframework-devicelibrary

Robot Framework Library for creating and interacting with devices using various adapters such as ssh, docker and local devices using the same interface.

# Using it

1. Install via pip

    ```sh
    pip install robotframework-devicelibrary[all]  git+https://github.com/reubenmiller/robotframework-devicelibrary.git@0.24.2
    ```

    Or add it to your `requirements.txt` file

    ```sh
    robotframework-devicelibrary[all] @ git+https://github.com/reubenmiller/robotframework-devicelibrary.git@0.24.2
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
