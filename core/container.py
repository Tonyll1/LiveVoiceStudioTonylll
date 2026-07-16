class Container:
    def __init__(self):
        self._services = {}

    def register(self, key, service):
        self._services[key] = service

    def get(self, key):
        if key not in self._services:
            raise KeyError(f"Servicio no registrado: {key}")

        return self._services[key]


container = Container()