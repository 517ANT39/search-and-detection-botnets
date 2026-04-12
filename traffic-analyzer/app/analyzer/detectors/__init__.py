# Импортируем все модули чтобы сработали декораторы @register
from app.analyzer.detectors import isolation_forest  # noqa: F401
from app.analyzer.detectors import port_scan          # noqa: F401
from app.analyzer.detectors import ddos               # noqa: F401
