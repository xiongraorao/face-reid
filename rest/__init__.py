from flask import Flask, jsonify
from rest.camera import camera
import pymysql
import configparser

app = Flask(__name__)

app.register_blueprint(camera, url_prefix='/camera')

if __name__ == '__main__':
    app.run()
