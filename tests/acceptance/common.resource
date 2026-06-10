*** Variables ***

# Adapter settings
${DEVICE_ADAPTER}    docker
&{SSH_CONFIG}        hostname=%{SSH_CONFIG_HOSTNAME= }    port=%{SSH_CONFIG_PORT= }    username=%{SSH_CONFIG_USERNAME= }    password=%{SSH_CONFIG_PASSWORD= }    configpath=%{SSH_CONFIG_CONFIGPATH= }
&{DOCKER_CONFIG}     image=%{DOCKER_CONFIG_IMAGE=debian-systemd}
