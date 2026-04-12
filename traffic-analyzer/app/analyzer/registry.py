import logging

from app.analyzer.base import BaseDetector

logger = logging.getLogger("analyzer.registry")


class DetectorRegistry:
    """
    Реестр детекторов. Позволяет регистрировать и получать все детекторы.

    Использование:
        @detector_registry.register
        class MyDetector(BaseDetector):
            ...
    """

    def __init__(self):
        self._detectors: dict[str, type[BaseDetector]] = {}

    def register(self, cls: type[BaseDetector]) -> type[BaseDetector]:
        """Декоратор для регистрации детектора."""
        instance = cls()
        name = instance.name
        if name in self._detectors:
            raise ValueError(f"Detector '{name}' already registered")
        self._detectors[name] = cls
        logger.info("Registered detector: %s", name)
        return cls

    def get_all(self) -> list[BaseDetector]:
        """Возвращает экземпляры всех зарегистрированных детекторов."""
        return [cls() for cls in self._detectors.values()]

    def get_by_name(self, name: str) -> BaseDetector | None:
        cls = self._detectors.get(name)
        return cls() if cls else None

    @property
    def names(self) -> list[str]:
        return list(self._detectors.keys())


# Глобальный реестр
detector_registry = DetectorRegistry()
