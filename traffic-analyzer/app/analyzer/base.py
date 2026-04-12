from abc import ABC, abstractmethod
from app.models import Alert, AnalyzerSettings


class BaseDetector(ABC):
    """
    Базовый класс для всех детекторов аномалий.

    Чтобы добавить новый детектор:
    1. Создай класс-наследник BaseDetector в app/analyzer/detectors/
    2. Реализуй name(), is_enabled(), detect()
    3. Зарегистрируй через @detector_registry.register
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя детектора."""
        ...

    @abstractmethod
    def is_enabled(self, settings: AnalyzerSettings) -> bool:
        """Включён ли детектор в настройках."""
        ...

    @abstractmethod
    def detect(self, settings: AnalyzerSettings) -> list[Alert]:
        """Запуск обнаружения. Возвращает список Alert (не сохранённых в БД)."""
        ...
