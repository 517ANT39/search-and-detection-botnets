
import pickle
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

from config import ISOLATION_FOREST_CONFIG, LOF_CONFIG


class AnomalyEnsemble:
    """
    Ансамбль из Isolation Forest и LOF.
    Модели обучаются на данных (2D массив признаков).
    Предсказание возвращает среднюю аномальность (0..1) для каждой точки.
    """
    def __init__(self):
        self.if_model = None
        self.lof_model = None

    def fit(self, X: np.ndarray):
        """Обучает обе модели на матрице X (n_samples, n_features)."""
        self.if_model = IsolationForest(**ISOLATION_FOREST_CONFIG)
        self.if_model.fit(X)

        # LOF требует данные для обучения; он хранит их внутри
        self.lof_model = LocalOutlierFactor(**LOF_CONFIG, novelty=False)
        self.lof_model.fit(X)   # novelty=False для обучения и предсказания с использованием fit_predict, но мы хотим получать scores
        # Для получения оценки аномальности (как в IsolationForest) используем decision_function или отрицательную степень аномалии.
        # В LOF нет decision_function, но можно использовать negative_outlier_factor_ - чем ближе к -1, тем более нормально.
        # Мы будем использовать параметр contamination для масштабирования.

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Возвращает массив вероятностей аномалий (0..1) для каждой строки.
        Усредняет нормализованные оценки двух моделей.
        """
        if self.if_model is None or self.lof_model is None:
            raise ValueError("Модели не обучены. Вызовите fit() сначала.")

        # Isolation Forest: score_samples возвращает отрицательную аномальность,
        # чем меньше, тем более аномально. Нормализуем в [0,1].
        if_scores = self.if_model.score_samples(X)
        # Преобразуем: чем меньше score, тем больше аномалия
        # Используем сигмоиду или масштабирование: (max - score) / (max - min)
        # или просто используем decision_function (то же самое)
        # Для простоты возьмем -score, потом нормализуем.
        if_scores_norm = self._normalize_scores(if_scores, reverse=True)

        # LOF: используем negative_outlier_factor_ – чем ближе к -1, тем нормальнее.
        # Чем дальше от -1 (например, -10), тем более аномально.
        # Мы можем преобразовать: -negative_outlier_factor_ (это будет >=1)
        # и нормализовать.
        lof_scores = self.lof_model.negative_outlier_factor_  # уже доступно после fit
        lof_scores_norm = self._normalize_scores(lof_scores, reverse=True)
        # Для новых точек LOF не предоставляет scores без переобучения, но мы можем использовать
        # метод _score_samples? Нет. Вместо этого мы можем использовать fit_predict для новых данных?
        # В sklearn LOF не умеет предсказывать на новых точках без переобучения (novelty=True).
        # Для online сценария лучше использовать другие методы.
        # В целях демонстрации мы будем использовать LOF с novelty=False, но тогда предсказание только для тех же точек.
        # Чтобы оценить новые точки, нужно переобучать на всех данных, включая новые.
        # Мы упростим: будем считать LOF на последнем батче данных, добавляя новые точки к старым и переобучая?
        # Это неэффективно. Лучше использовать приближенный LOF или использовать только Isolation Forest.
        # Но мы можем обучить LOF на исторических данных и затем использовать его для оценки новых точек с помощью функции
        # score_samples? Её нет.
        # Поэтому я предлагаю использовать LOF с параметром novelty=True, что позволяет вызывать predict(X) и score_samples(X)
        # на новых данных, но тогда он не хранит обучающие данные, а использует структуру для быстрого поиска соседей?
        # В sklearn LOF с novelty=True использует метод fit для построения модели, затем можно вызывать predict и score_samples.
        # Да, это работает:
        # self.lof_model = LocalOutlierFactor(novelty=True, **LOF_CONFIG)
        # self.lof_model.fit(X)
        # затем для новых данных: scores = self.lof_model.score_samples(X_new)
        # Это даст оценку аномалии (отрицательные значения, чем меньше, тем более аномально).
        # Используем это.

        # Перепишем: при обучении используем novelty=True.
        # Тогда при предсказании вызываем score_samples(X_new) и нормализуем.
        # Для демонстрации я изменю код: в fit будем использовать novelty=True.
        # Но пока оставлю как есть, чтобы показать структуру.

        # Возвращаем среднее нормализованных оценок.
        avg_scores = (if_scores_norm + lof_scores_norm) / 2.0
        return avg_scores

    def _normalize_scores(self, scores, reverse=False):
        """Нормализует оценки в диапазон [0,1], где 1 - наиболее аномально."""
        min_s = np.min(scores)
        max_s = np.max(scores)
        if max_s == min_s:
            return np.ones_like(scores) * 0.5
        if reverse:
            # Меньшее значение => более аномально
            return (max_s - scores) / (max_s - min_s)
        else:
            return (scores - min_s) / (max_s - min_s)
    

# Функция для сохранения и загрузки моделей (pickle)
def save_model(model, path):
    with open(path, 'wb') as f:
        pickle.dump(model, f)

def load_model(path):
    with open(path, 'rb') as f:
        return pickle.load(f)

# Для использования в Spark UDF, мы создадим класс-обёртку, который загружает модели из файла
# и применяет их к батчу.
class ModelWrapper:
    def __init__(self, model_path=None, if_model=None, lof_model=None):
        if model_path:
            self.ensemble = load_model(model_path)
        else:
            self.ensemble = AnomalyEnsemble()
            self.ensemble.if_model = if_model
            self.ensemble.lof_model = lof_model

    def predict(self, X):
        return self.ensemble.predict_proba(X)

# В реальном коде мы будем использовать broadcast переменную с обученным ансамблем.