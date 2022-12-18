from DeviceLibrary import DeviceLibrary


def test_docker_device():
    adapter = DeviceLibrary(adapter="docker")
    adapter.start()
