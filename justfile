
# Note: Windows stores virtual environment scripts under Scripts/ directory instead of bin/
venv_bin := if os_family() == "windows" { ".venv/Scripts" } else { ".venv/bin" }

ssh_device_name := "devicelibrary-ssh-device"

# Install python virtual environment
venv:
    [ -d .venv ] || python3 -m venv .venv
    {{venv_bin}}/python3 -m pip install -e ".[all]"

# Build the docker image used by the acceptance tests
# (it is also used as the target device for the ssh adapter tests)
build-test-images:
    docker build -t debian-systemd tests/images/debian-systemd

# Start an ssh-able test device to run the ssh adapter acceptance tests against
start-ssh-device port="2222": build-test-images
    # Remove any stale known_hosts entry as the image generates a new host key on each build
    -ssh-keygen -R "[127.0.0.1]:{{port}}" 2>/dev/null
    docker run -d --rm --name {{ssh_device_name}} --privileged --tmpfs /run --tmpfs /tmp -p {{port}}:22 debian-systemd
    @echo ""
    @echo "Use the following settings (e.g. add them to your .env file):"
    @echo "  SSH_CONFIG_HOSTNAME=127.0.0.1"
    @echo "  SSH_CONFIG_PORT={{port}}"
    @echo "  SSH_CONFIG_USERNAME=root"
    @echo "  SSH_CONFIG_PASSWORD=inttest"

# Stop the ssh test device
stop-ssh-device:
    docker rm -f {{ssh_device_name}}

# Run the tests (local, ssh, docker and docker compose adapters).
# Requires the test image (build-test-images) and a running ssh test
# device (start-ssh-device)
test *ARGS:
    {{venv_bin}}/python3 -m robot --outputdir output {{ARGS}} tests/acceptance

# Generate the keyword documentation
docs:
    {{venv_bin}}/python3 -m robot.libdoc DeviceLibrary/DeviceLibrary.py docs/DeviceLibrary.rst
