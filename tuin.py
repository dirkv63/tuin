import platform
from tuin import create_app
from tuin.db_model import User
from waitress import serve


# Run Application
if __name__ == "__main__":
    env = "development"
    if platform.node() == "zeegeus":
        env = "production"
    app = create_app(env)

    with app.app_context():
        if User.query.filter_by(username='dirk').first() is None:
            User.register('dirk', 'olse')

        if env == "development":
            app.run()
        else:
            serve(app, listen='127.0.0.1:8005')
