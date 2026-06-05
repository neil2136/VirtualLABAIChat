import logging
import os

basedir = os.path.abspath(os.path.dirname(__file__))

MONGODB_CONFIG = {
    'host': '10.103.2.40',
    'port': 27017,
    'db_name': 'VL',
    'username': 'root',
    'password': 'sonicpassword'
    }

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'mail.sonicwall.com')
    # MAIL_SERVER = os.environ.get('MAIL_SERVER', '10.50.129.54')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '25'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    FLASKY_MAIL_SUBJECT_PREFIX = '[QA LAB]'
    FLASKY_MAIL_SENDER = 'VLAB Admin <lezhang@sonicwall.com>'
    FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')
    SSL_REDIRECT = True
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLALCHEMY_RECORD_QUERIES = True
    FLASKY_POSTS_PER_PAGE = 20
    FLASKY_FOLLOWERS_PER_PAGE = 50
    FLASKY_COMMENTS_PER_PAGE = 30
    FLASKY_SLOW_DB_QUERY_TIME = 0.5
    # 默认日志等级
    LOG_LEVEL = logging.WARNING

    # CELERY_BROKER_URL = 'redis://localhost:6379/0'
    # CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    #ticket mail admin account
    # defaultadmin = 'Roger (Qinjie) Gu'
    # defaultsendto1 = 'qigu@SonicWall.com'
    # defaultsendto2 = 'lezhang@SonicWall.com'
    #log dir
    log_system_dir = 'app/logs/system.log'
    

    # DeepSeek API Configuration
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY') or 'sk-13345426129f4b51ac830ab5929a6d5e'
    DEEPSEEK_API_BASE_URL = 'https://api.deepseek.com/v1'
    DEEPSEEK_MODEL = 'deepseek-chat'
    DEEPSEEK_MAX_TOKENS = 2000
    DEEPSEEK_TEMPERATURE = 0.7

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = logging.WARNING
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
    #     'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    # SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
    #     'sqlite://'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #     'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    """生产模式下的配置"""
    LOG_LEVEL = logging.WARNING

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # email errors to the administrators
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.FLASKY_MAIL_SENDER,
            toaddrs=[cls.FLASKY_ADMIN],
            subject=cls.FLASKY_MAIL_SUBJECT_PREFIX + ' Application Error',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


class HerokuConfig(ProductionConfig):
    SSL_REDIRECT = True if os.environ.get('DYNO') else False

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # handle reverse proxy server headers
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)


class DockerConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class UnixConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # log to syslog
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.ERROR)
        app.logger.addHandler(syslog_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'docker': DockerConfig,
    'unix': UnixConfig,

    'default': DevelopmentConfig
}
