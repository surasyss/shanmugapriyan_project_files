from spices.import_utils import import_modules

_SENTINEL = object()


class _ConnectorRegistry:
    def __init__(self):
        self._registry = {}

    def get(self, code: str, default=_SENTINEL) -> type:
        """Get connector for the code"""
        value = self._registry.get(code, default)
        if value == _SENTINEL:
            raise KeyError(f'No connector registered for code "{code}"')
        return value

    def register(self, code: str, connector: type):
        """Register a connector with a code"""
        existing = self._registry.get(code)
        if existing:
            raise ValueError(
                f'The code "{code}" has already been registered before with {existing}'
            )
        if not isinstance(connector, type):
            raise TypeError(
                f"Expected connector to be a class, received a {type(connector)}"
            )
        self._registry[code] = connector

    def add(self, code: str):
        """Decorator form of the register method"""

        def _internal_register(cls):
            """Register this class with the code provided in the decorator call"""
            self.register(code, cls)
            return cls

        return _internal_register


connectors = _ConnectorRegistry()
import_modules("apps.adapters.vendors")
import_modules("apps.adapters.accounting")
