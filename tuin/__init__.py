# import os
from config import config
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from lib import my_env

bootstrap = Bootstrap()
db = SQLAlchemy()
lm = LoginManager()
lm.login_view = 'main.login'


def create_app(config_name):
    """
    Create an application instance.
    :param config_name: development, test or production
    :return: the configured application object.
    """
    app = Flask(__name__)

    # import configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Configure Logger
    my_env.init_loghandler(__name__, app.config.get('LOGDIR'), app.config.get('LOGLEVEL'))

    # initialize extensions
    bootstrap.init_app(app)
    db.init_app(app)
    lm.init_app(app)

    # import blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # add Jinja Filters
    app.jinja_env.filters['datestamp'] = my_env.datestamp
    app.jinja_env.filters['reformat_body'] = my_env.reformat_body
    app.jinja_env.filters['children_sorted'] = my_env.children_sorted
    app.jinja_env.filters['fix_urls'] = my_env.altfix_urls
    app.jinja_env.filters['nodes_sorted'] = my_env.nodes_sorted
    app.jinja_env.filters['terms_sorted'] = my_env.terms_sorted

    # configure production logging of errors
    """
    try:
        app.config['PRODUCTION']
    except KeyError:
        # Running in Dev or Test, OK
        pass
    else:
        from logging.handlers import SMTPHandler
        mail_handler = SMTPHandler('127.0.0.1', 'dirk@vermeylen.net', app.config['ADMINS'], 'Application Error')
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
    """
    return app
