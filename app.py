from flask import Flask

from rest import camera

app = Flask(__name__)
app.register_blueprint(camera, url_prefix='/camera')

if __name__ == '__main__':
    app.run('0.0.0.0')
