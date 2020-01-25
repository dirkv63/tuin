# import os
import rq
from config import Config
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from redis import Redis
from tuin.lib import my_env

bootstrap = Bootstrap()
db = SQLAlchemy()
lm = LoginManager()
lm.login_view = 'main.login'


def create_app(config_class=Config):
    """
    Create an application instance.

    :param config_class: Pointer to the config class.
    :return: the configured application object.
    """

    app = Flask(__name__)

    # import configuration
    app.config.from_object(config_class)

    # Configure Logger, except for Test
    if not app.testing:
        hdl = my_env.init_loghandler(__name__)
        app.logger.addHandler(hdl)

    app.logger.info("Start Application")

    # initialize extensions
    bootstrap.init_app(app)
    db.init_app(app)
    lm.init_app(app)

    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('tuin-tasks', connection=app.redis)

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
    app.jinja_env.filters['monthdisp'] = my_env.monthdisp

    return app
