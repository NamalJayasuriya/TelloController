import os
import socket
import queue
import threading
import time
import datetime

import cv2
import numpy as np
import paddlehub as hub
from PIL import Image

from stats import Stats
# from video import VideoCamera, run_app
import torch
q = queue.Queue()


# q.queue.clear()


class Tello:
    def __init__(self, te_ip: str = '192.168.10.1', debug: bool = True):
        # 在8889上打开本地UDP端口以进行无人机通信
        self.local_ip = ''
        self.local_port = 8889
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.local_ip, self.local_port))

        # 设置无人机IP和端口信息
        self.te_ip = te_ip
        self.te_port = 8889
        self.te_address = (self.te_ip, self.te_port)
        self.log = []
        self.picture_path = ''
        self.file_path = ''
        self.frame = None

        # Defining Object detection model
        # self.module = hub.Module(name="ultra_light_fast_generic_face_detector_1mb_640")
        # --------------
        # self.hog = cv2.HOGDescriptor()
        # self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        # -------------------
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        self.model.conf = 0.4  # set inference threshold at 0.3
        self.model.iou = 0.3  # set inference IOU threshold at 0.3
        self.model.classes = [0, 15, 16, 24, 25, 26, 39, 41, 42, 43, 44, 56,57,59,62,63,67,73]  # set model to only detect "Person" class
        self.classes = {0:'person', 15:'cat', 16:'dog', 24:'backpack', 25:'umbrella', 26:'handbag', 39:'bottle', 41:'cup', 42:'fork', 43:'knife', 44:'spoon', 45:'bowl', 56:'chair' ,57:'couch' ,59:'bed', 60:'dinning_table' ,62:'tv' ,63:'laptop' ,67:'phone', 73:'book', 75:'vase'}
        #-----------------------

        # 初始化响应线程
        self.receive_thread = threading.Thread(target=self._receive_thread)
        self.receive_thread.daemon = True
        self.receive_thread.start()

        # 本项目运行时选项
        self.stream_state = False
        self.camera_state = False
        self.color_state = False
        self.video_state = False
        self.save_state = False
        self.picture_state = False
        self.animal_state = False
        self.flip_frame = False
        self.now_color = 0
        self.MAX_TIME_OUT = 15.0
        self.debug = debug
        self.command_ready = True

        # 将无人机设置为命令模式
        self.command()

    def score_frame(self, frame):
        """
        function scores each frame of the video and returns results.
        :param frame: frame to be infered.
        :return: labels and coordinates of objects found.
        """
        self.model.to(self.device)
        results = self.model([frame])
        labels, cord = results.xyxyn[0][:, -1].to('cpu').numpy(), results.xyxyn[0][:, :-1].to('cpu').numpy()
        return labels, cord

    def plot_boxes(self, results, frame):
        """
        plots boxes and labels on frame.
        :param results: inferences made by model
        :param frame: frame on which to  make the plots
        :return: new frame with boxes and labels plotted.
        """
        labels, cord = results
        n = len(labels)
        x_shape, y_shape = frame.shape[1], frame.shape[0]
        for i in range(n):
            row = cord[i]
            x1, y1, x2, y2 = int(row[0]*x_shape), int(row[1]*y_shape), int(row[2]*x_shape), int(row[3]*y_shape)
            bgr = (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), bgr, 1)
            label = f"{int(row[4]*100)}"
            label = "{0}:{1}".format(self.classes[int(labels[i])], label)
            cv2.putText(frame, label, (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            cv2.putText(frame, f"Total Targets: {n}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return frame

    def send_command(self, command: str, query: bool = False):

        # self.command_ready = False # added by NAmal

        # 为出站命令创建新的日志条目
        self.log.append(Stats(command, len(self.log)))

        # 向无人机发送命令
        self.socket.sendto(command.encode('utf-8'), self.te_address)
        # 显示确认消息

        if self.debug is True:
            print('Send Command: {}'.format(command))

        # 检查命令是否超时（基于MAX_TIME_OUT中的值）
        start = time.time()
        while not self.log[-1].got_response():  # 在日志中未收到任何响应的情况下运行
            now = time.time()
            difference = now - start
            if difference > self.MAX_TIME_OUT:
                print('Connect Time Out!')
                break

        # 打印出无人机响应
        if self.debug is True and query is False:
            print('Response: {}'.format(self.log[-1].get_response()))

    def _receive_thread(self):
        while True:
            # 检查无人机响应，引发套接字错误
            try:
                self.response, ip = self.socket.recvfrom(1024)
                self.log[-1].add_response(self.response)
            except socket.error as exc:
                print('Error: {}'.format(exc))

    def _cap_video_thread(self):
        # 创建流捕获对象
        cap = cv2.VideoCapture('udp://' + self.te_ip + ':11111')  #'udp://192.168.10.1:11111'

        # cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

        while self.stream_state:
            ret, frame = cap.read()
            # seq += 1
            while ret:
                ret, frame = cap.read()
                if self.flip_frame:
                    frame = cv2.flip(frame, 0)

                # # --- added by namal ---
                # # resizing for faster detection
                # frame = cv2.resize(frame, (640, 480))
                # # using a greyscale picture, also for faster detection
                # gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                #
                # # detect people in the image
                # # returns the bounding boxes for the detected objects
                # boxes, weights = self.hog.detectMultiScale(frame, winStride=(8, 8))
                #
                # boxes = np.array([[x, y, x + w, y + h] for (x, y, w, h) in boxes])
                #
                # if len(boxes) > 0:
                #     print("Human detected")
                #
                # for (xA, yA, xB, yB) in boxes:
                #     # display the detected boxes in the colour picture
                #     cv2.rectangle(frame, (xA, yA), (xB, yB),
                #                   (0, 255, 0), 2)
                # # ------
                #------------------
                # resizing for faster detection
                # frame = cv2.resize(frame, (640, 480))
                results = self.score_frame(frame)
                frame = self.plot_boxes(results, frame)
                #------------------

                cv2.imshow("DJI Tello", frame)
                q.put(frame)
                k = cv2.waitKey(1) & 0xFF
                # 如果按Esc键，视频流关闭
                if k == 27:
                    break
        cap.release()
        cv2.destroyAllWindows()

    def _service_video_thread(self):
        while True:
            self.frame = q.get()
            # k = cv2.waitKey(1) & 0xFF
            # 如果按F1键，截图到当前位置
            # if k == 0 or self.camera_state:
            if self.camera_state:
                self.file_path = self.picture_path + '\\' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '.png'
                print('图片路径为：', self.file_path)
                try:
                    cv2.imwrite(self.file_path, self.frame)
                except Exception as e:
                    print('保存图片失败')
                self.camera_state = False

            # 识别动物
            if self.animal_state:
                # results = self.module.face_detection(images=[self.frame],visualization = True, output_dir = 'DETECTED')
                # print(results)
                # key_value_list = list(results[0].items())
                # key_first, value_first = key_value_list[0][0], key_value_list[0][1]
                # print(key_first) # Edited By Namal
                # if '非动物' != key_first:
                #     # print('检测结果是：', key_first, '，相似度为：', value_first)
                #     cv2.imshow(key_first, self.frame)
                #     self.animal_state = False

                # --- added by namal ---
                # resizing for faster detection
                frame = cv2.resize(self.frame, (640, 480))
                # using a greyscale picture, also for faster detection
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

                # detect people in the image
                # returns the bounding boxes for the detected objects
                boxes, weights = self.hog.detectMultiScale(frame, winStride=(8, 8))

                boxes = np.array([[x, y, x + w, y + h] for (x, y, w, h) in boxes])

                if len(boxes) > 0:
                    print("Human detected")

                for (xA, yA, xB, yB) in boxes:
                    # display the detected boxes in the colour picture
                    cv2.rectangle(frame, (xA, yA), (xB, yB),
                                  (0, 255, 0), 2)
                self.frame = frame
                # # Write the output video
                # out.write(frame.astype('uint8'))
                # # Display the resulting frame
                #self.animal_state = False
                # self.streamoff()
                # self.stream_state = False
                # self.video_state = False
                #cv2.imshow('frame', self.frame)

                # ----------------------

            # 显示照片
            if self.picture_state:
                file = self.file_path
                f = Image.open(file).show()
                self.picture_state = False

            # 识别当前颜色
            if self.color_state:
                self.detect_color(self.frame)
                self.color_state = False

            # 将视频流发送至http
            if self.video_state:
                self.video_http(self.frame)
                self.video_state = False

            # 保存视频流至本地
            if self.save_state:
                self.video_save(self.frame)
                self.save_state = False

    def wait(self, delay: float):
        # 显示等待消息
        if self.debug is True:
            print('Wait {} Seconds...'.format(delay))

        # 日志条目增加了延迟
        self.log.append(Stats('wait', len(self.log)))
        # 延迟激活
        time.sleep(delay)

    # @staticmethod
    # def video_http(frame):
    #     # vc = VideoCamera(frame)
    #     # run_app()
    #
    # @staticmethod
    # def video_save(frame):
    #     force = cv2.VideoWriter_fourcc(*'XVID')
    #     out = cv2.VideoWriter('output.avi', force, 20.0, (640, 480))
    #     frame = cv2.flip(frame, 0)
    #     # write the flipped frame
    #     out.write(frame)

    def get_log(self):
        return self.log

    def take_picture(self, path=os.getcwd()):
        """拍照"""
        self.camera_state = True
        self.picture_path = path

    def show_picture(self):
        """显示照片"""
        self.picture_state = True

    def flip_video(self):
        """翻转视频，在加装下视镜片的情况下开启"""
        self.flip_frame = True

    def identify_animal(self):
        """识别动物"""
        self.animal_state = True

    def identify_color(self):
        """识别当前颜色(红色或绿色)"""
        self.color_state = True
        time.sleep(0.5)
        return self.now_color

    # 以下命令强烈建议配合官方SDK食用
    # https://www.ryzerobotics.com/cn/tello/downloads

    # 控制命令
    def command(self):
        """进入SDK命令模式"""
        self.send_command('command')

    def takeoff(self):
        """自动起飞，1米左右"""
        self.send_command('takeoff')

    def land(self):
        """自动降落"""
        self.send_command('land')

    def streamon(self):
        """打开视频流"""
        self.send_command('streamon')
        print(self.te_ip)
        self.stream_state = True

        self.cap_video_thread = threading.Thread(target=self._cap_video_thread)
        self.cap_video_thread.daemon = True
        self.cap_video_thread.start()

    def streamoff(self):
        """关闭视频流"""
        self.stream_state = False
        self.send_command('streamoff')

    def stream_service_on(self):
        """是否开启视频流附加功能，开启视频流会卡顿"""
        self.service_video_thread = threading.Thread(target=self._service_video_thread)
        self.service_video_thread.daemon = True
        self.service_video_thread.start()


    def set_resolution(self, res):
        if res == 480:
            self.send_command('setresolution low')
        elif res ==720:
            self.send_command('setresolution high')
        else:
            print(" Invalid Resolution : Set 480P or 720P")
    def set_fps(self, res):
        if res == 5:
            self.send_command('setfps low')
        elif res ==15:
            self.send_command('setfps middle')
        elif res == 30:
            self.send_command('setfps high')
        else:
            print("Invalid frame rate: Set 5, 15 or 30")

    def detect_color(self, frame):
        """颜色识别"""
        # frame = cv2.imread("test.jpg")
        hue_image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        low_red_range1 = np.array([110, 43, 0])
        high_red_range1 = np.array([180, 255, 255])
        threshold_red1 = cv2.inRange(hue_image, low_red_range1, high_red_range1)
        res_red1 = cv2.bitwise_and(frame, frame, mask=threshold_red1)

        low_red_range2 = np.array([0, 43, 0])
        high_red_range2 = np.array([10, 255, 255])
        threshold_red2 = cv2.inRange(hue_image, low_red_range2, high_red_range2)
        res_red2 = cv2.bitwise_and(frame, frame, mask=threshold_red2)

        threshold_red = threshold_red1 + threshold_red2
        res_red = res_red1 + res_red2

        low_green_range = np.array([35, 43, 46])
        high_green_range = np.array([77, 255, 255])
        threshold_green = cv2.inRange(hue_image, low_green_range, high_green_range)
        res_green = cv2.bitwise_and(frame, frame, mask=threshold_green)

        res = res_red + res_green
        if cv2.countNonZero(threshold_green) > 0.5 * np.size(threshold_green):
            self.now_color = 'green'
        elif ((cv2.countNonZero(threshold_red) > 0.5 * np.size(threshold_red)) & (
                cv2.countNonZero(threshold_red) < 0.7 * np.size(threshold_red))):
            self.now_color = 'red'
        else:
            self.now_color = 'none'
            # color = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        return self.now_color, res

    def emergency(self):
        """停止电机转动"""
        self.send_command('emergency')

    def up(self, x: int):
        """向上飞x（20-500）厘米"""
        self.send_command('up {}'.format(x))

    def down(self, x: int):
        """向下飞x（20-500）厘米"""
        self.send_command('down {}'.format(x))

    def left(self, x: int):
        """向左飞x（20-500）厘米"""
        self.send_command('left {}'.format(x))

    def right(self, x: int):
        """向右飞x（20-500）厘米"""
        self.send_command('right {}'.format(x))

    def forward(self, x: int):
        """向前飞x（20-500）厘米"""
        self.send_command('forward {}'.format(x))

    def back(self, x: int):
        """向后飞x（20-500）厘米"""
        self.send_command('back {}'.format(x))

    def cw(self, angle: int):
        """顺时针旋转angle°（1-360）"""
        self.send_command('cw {}'.format(angle))

    def ccw(self, angle: int):
        """逆时针旋转angle°（1-360）"""
        self.send_command('ccw {}'.format(angle))

    def flip(self, direction: str):
        """朝direction方向翻滚，左侧（left）缩写为l，同理right=r，forward=f，back=b"""
        self.send_command('flip {}'.format(direction))

    def go(self, x: int, y: int, z: int, speed: int):
        """以设置速度speed（cm / s）飞往坐标（x, y, z）
            x: -500 - 500
            y: -500 - 500
            z: -500 - 500
            speed: 10 - 100(cm / s)
        x、y、z不能同时在 -20 ~ 20 之间"""
        self.send_command('go {} {} {} {}'.format(x, y, z, speed))

    def stop(self):
        """"停止运动并悬停，任何时候都可以"""
        self.send_command('stop')

    def curve(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int):
        """以设置速度speed（ cm/s ）飞弧线，经过（x1,y1,z1）到（x2,y2,z2）
        如果弧线半径不在 0.5-10 米范围内，则返回相应提醒
            x1, x2: -500 - 500
            y1, y2: -500 - 500
            z1, z2: -500 - 500
            speed: 10-60
        x、y、z 不能同时在 -20 ~ 20 之间"""
        self.send_command('curve {} {} {} {} {} {} {}'.format(x1, y1, z1, x2, y2, z2, speed))

    def go_mid(self, x: int, y: int, z: int, speed: int, mid: str):
        """以设置速度speed（m/s）飞往设置 id 的挑战卡坐标系的（x,y,z）坐标点
            mid:
                m1/m2/~/m8：对应挑战卡上的挑战卡ID
                m-1: 无人机内部算法最快识别到的挑战卡，随机选择一个探测到的挑战卡
                m-2: 距离无人机中心距离最近的挑战卡
            x: -500 - 500
            y: -500 - 500
            z: 0 - 500
            speed: 10-100 (cm/s)
        x、y、z 不能同时在 -20 ~ 20 之间"""
        self.send_command('go {} {} {} {} {}'.format(x, y, z, speed, mid))

    def curve_mid(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int, mid: str):
        """以设置速度speed（ cm/s ）飞弧线，经过设置 mid 的挑战卡坐标系中的（x1,y1,z1）点到（x2,y2,z2）点
        如果弧线半径不在 0.5-10 米范围内，则返回相应提醒
            x1, x2: -500 - 500
            y1, y2: -500 - 500
            z1, z2: 0 - 500
            speed: 10-60
        x、y、z 不能同时在 -20 ~ 20 之间"""
        self.send_command('curve {} {} {} {} {} {} {} {}'.format(x1, y1, z1, x2, y2, z2, speed, mid))

    def jump_mid(self, x: int, y: int, z: int, speed: int, yaw: int, mid1: str, mid2: str):
        """飞往 mid1 坐标系的（x,y,z）点后悬停，识别 mid2 的挑战卡
        并在 mid2 坐标系下 (0,0,z) 的位置并旋转向到设置的 偏航yaw 值，( z>0 )"""
        self.send_command('jump {} {} {} {} {} {} {}'.format(x, y, z, speed, yaw, mid1, mid2))

    # 设置命令
    def set_speed(self, speed: int):
        """将当前速度设为 speed cm/s，speed = 10-100"""
        self.send_command('speed {}'.format(speed))

    def rc_control(self, a: int, b: int, c: int, d: int):
        """设置遥控器的 4 个通道杆量
            a: 横滚 (-100~100)
            b: 俯仰 (-100~100)
            c: 油门 (-100~100)
            d: 偏航 (-100~100)
        """
        self.send_command('rc {} {} {} {}'.format(a, b, c, d))

    def set_wifi(self, ssid: str, passwrd: str):
        """更改 无人机 Wi-Fi 密码
            ssid: 更改后的 Wi-Fi 账号
            passwrd: 更改后的 Wi-Fi 密码
        """
        self.send_command('wifi {} {}'.format(ssid, passwrd))

    def mon(self):
        """"打开挑战卡探测，默认同时打开前视和下视探测"""
        self.send_command('mon')

    def moff(self):
        """"关闭挑战卡探测"""
        self.send_command('moff')

    def mdirection(self, mdir: int):
        """mdir=0/1/2
            0 打开下视探测
            1 打开前视探测
            2 同时打开前视和下视探测
        * 使用前必须使用 mon 命令打开探测功能
        * 单独打开前视或者下视探测时，探测频率为20Hz，同时打开前视和下视时，将交替探测，单个反向的探测频率为 10Hz"""
        self.send_command('mdirection {}'.format(mdir))

    def ap2sta(self, ssid: str, passwrd: str):
        """将Tello转为 station 模式，并连入到 AP
            ssid: 要连接的 Wi-Fi 账号
            passwrd: 要连接的 Wi-Fi 密码"""
        self.send_command('ap {} {}'.format(ssid, passwrd))

    # 读取命令
    def get_speed(self):
        """获取当前设置速度speed（cm/s），speed(10-100)"""
        self.send_command('speed?', True)
        return self.log[-1].get_response()

    def get_battery(self):
        """获取当前电池剩余电量的百分比值 x，x = (10-100)"""
        self.send_command('battery?', True)
        return self.log[-1].get_response()

    def get_time(self):
        """获取电机运转时间（s）"""
        self.send_command('time?', True)
        return self.log[-1].get_response()

    def get_wifi(self):
        """获得 Wi-Fi 信噪比"""
        self.send_command('wifi?', True)
        return self.log[-1].get_response()

    def get_sdk(self):
        """获得 无人机 SDK 版本号 xx(>=20)"""
        self.send_command('sdk?', True)
        return self.log[-1].get_response()

    def get_sn(self):
        """获得 无人机 SN 码 生产序列号"""
        self.send_command('sn?', True)
        return self.log[-1].get_response()

    def get_height(self):
        """获取高度，新版本中已停用"""
        self.send_command('height?', True)
        return self.log[-1].get_response()

    def get_temp(self):
        """获取温度，新版本中已停用"""
        self.send_command('temp?', True)
        return self.log[-1].get_response()

    def get_attitude(self):
        """获取飞行姿态，新版本中已停用"""
        self.send_command('attitude?', True)
        return self.log[-1].get_response()

    def get_baro(self):
        """获取压力，新版本中已停用"""
        self.send_command('baro?', True)
        return self.log[-1].get_response()

    def get_acceleration(self):
        """获取加速度，新版本中已停用"""
        self.send_command('acceleration?', True)
        return self.log[-1].get_response()

    def get_tof(self):
        """获取飞行时间，新版本中已停用"""
        self.send_command('tof?', True)
        return self.log[-1].get_response()
