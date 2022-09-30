from flask import Flask, render_template, Response
import cv2

import numpy as np


class VideoCamera(object):
    def __init__(self, frame):
        self.video = frame

    def __del__(self):
        self.video.release()

    def get_frame(self):
        success, image = self.video.read()

        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()


app = Flask(__name__)


@app.route('/')  # 主页
def index():
    return render_template('index.html')


def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()), mimetype='multipart/x-mixed-replace; boundary=frame')


def run_app():
    app.run(host='0.0.0.0', debug=True, port=5000)


if __name__ == '__main__':
    # initialize the HOG descriptor/person detector
    run_app()
