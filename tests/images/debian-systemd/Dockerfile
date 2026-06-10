# Test image used by the acceptance tests.
#
# It mimics a typical debian device running systemd, and is used both as
# the docker adapter's device image and as the target device for the ssh
# adapter tests (it runs an openssh-server which allows root login using
# a password).
#
# NOTE: This image is strictly for testing, don't use it for anything else!
FROM debian:12-slim

ARG ROOT_PASSWORD=inttest

ENV DEBIAN_FRONTEND=noninteractive
ENV container=docker

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        systemd \
        systemd-sysv \
        dbus \
        openssh-server \
        sudo \
        curl \
        ca-certificates \
        procps \
    && rm -rf /var/lib/apt/lists/*

# Allow logging in as root via ssh with a password (test image only!)
RUN echo "root:${ROOT_PASSWORD}" | chpasswd \
    && sed -i 's/#\?PermitRootLogin .*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#\?PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && systemctl enable ssh

# Debian ships 'D /tmp' which makes systemd-tmpfiles wipe the contents of
# /tmp during boot, racing with tests which start as soon as the container
# is running. Override it so /tmp is left alone ('d' creates but never purges)
RUN echo 'd /tmp 1777 root root -' > /etc/tmpfiles.d/tmp.conf

STOPSIGNAL SIGRTMIN+3

CMD ["/lib/systemd/systemd"]
