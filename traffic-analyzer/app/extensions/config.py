import yaml


def _load(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


_c = _load()


class Config:
    SECRET_KEY = _c["app"]["secret_key"]
    DEBUG = _c["app"].get("debug", False)
    LOG_LEVEL = _c.get("log_level", "info").upper()

    SQLALCHEMY_DATABASE_URI = _c["postgres"]["uri"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CH_HOST = _c["clickhouse"]["host"]
    CH_PORT = _c["clickhouse"]["port"]
    CH_DATABASE = _c["clickhouse"]["database"]
    CH_USERNAME = _c["clickhouse"]["username"]
    CH_PASSWORD = _c["clickhouse"]["password"]

    MAIL_SERVER = _c["mail"]["server"]
    MAIL_PORT = _c["mail"]["port"]
    MAIL_USE_TLS = _c["mail"]["use_tls"]
    MAIL_USERNAME = _c["mail"]["username"]
    MAIL_PASSWORD = _c["mail"]["password"]
    MAIL_DEFAULT_SENDER = _c["mail"]["default_sender"]

    ANALYZER_SCHEDULE_MINUTES = _c["analyzer"]["schedule_minutes"]
    ANALYZER_CONTAMINATION = _c["analyzer"]["contamination"]
    ANALYZER_N_ESTIMATORS = _c["analyzer"]["n_estimators"]
    ANALYZER_WINDOW_MINUTES = _c["analyzer"]["window_minutes"]
    ANALYZER_MIN_SAMPLES = _c["analyzer"]["min_samples"]

    SCHEDULER_API_ENABLED = True
    BABEL_DEFAULT_LOCALE = "ru"
