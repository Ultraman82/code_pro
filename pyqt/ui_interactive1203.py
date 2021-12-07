#!/usr/bin/env python
# coding: utf-8

import sys
import os
import cv2
import time
import subprocess

from monitor import detect, LoadImages
from PyQt5.QtWidgets import QDialog, QMainWindow, QApplication, QSlider, QFileDialog, QLabel, QPushButton, QFrame, QTextEdit, QProgressBar, QAction
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot, QUrl
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import uic, QtMultimedia

from qt_material import apply_stylesheet, list_themes

from collections import deque

UNINITIALIZED = 0
INITIALIZED = 1
INFERENCE_INITIALIZED = 2
PLAYING = 3
STOPPED = 4
INFERENCE_FINISHED = 5
RECORD_FINISHED = 6


class ClickableLabel(QLabel):
    clicked = pyqtSignal(int)

    def __init__(self, parent=None, id=0):
        QLabel.__init__(self, parent)
        self.id = id
        self.setFrameShape(QFrame.Box)
        self.setScaledContents(True)
        self.setFixedSize(100, 100)

    def mousePressEvent(self, event):
        self.clicked.emit(self.id)
        super(ClickableLabel, self).mousePressEvent(event)


class IncodingThread(QThread):
    record_signal = pyqtSignal(int)
    record_progress = pyqtSignal(str)

    def __init__(self, val, parent=None):
        super(IncodingThread, self).__init__(parent)
        self.out_dir = val

    def run(self):
        t0 = time.time()
        iamges_path = f"./{self.out_dir}/%08d.jpg"
        codecs = "-c:v"
        out_file = "out.mp4"
        p = subprocess.Popen(
            ["ffmpeg", "-y", "-r", "30", "-i", iamges_path, codecs, "h264", out_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for line in p.stdout:
            if line.startswith("frame="):
                self.record_progress.emit(line[:20])
        # while True:
        #     line = p.stdout.readline()
        #     if not line:
        #         break
        #     print(type(line))

        print(f'Done. ({time.time() - t0:.3f}s)')
        self.record_signal.emit(RECORD_FINISHED)


class VideoThread(QThread):
    changePixmap = pyqtSignal(list)
    frame_signal = pyqtSignal(int)

    def __init__(self, val, parent=None):
        super(VideoThread, self).__init__(parent)
        self.frame_n = 1
        self.instances = {}
        self.class_infos = {}
        self.total_frame = val.total_frame
        # self.instance_cls = val.instance_cls
        self.mode = val.mode
        self.inference_status = val.inference_status
        self.out_dir = val.out_dir

    def convert2qtimage(self, img_path, scale_x, scale_y):
        frame = cv2.imread(img_path)
        rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgbImage.shape
        bytesPerLine = ch * w
        convertToQtFormat = QImage(
            rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
        p = convertToQtFormat.scaled(scale_x, scale_y, Qt.KeepAspectRatio)
        return p

    def update_imgage(self):
        # print(f"frame_n:{self.frame_n}")
        img_path = self.out_dir + f"/{self.frame_n:08d}.jpg"
        print(img_path)
        images = [self.convert2qtimage(img_path, 1280, 720)]
        if self.frame_n in self.instances:
            instance_data = self.instances[self.frame_n]
            # print(self.class_infos[self.frame_n])
            for i in instance_data:
                images.append(self.convert2qtimage(i, 400, 300))
                # instance_crop = baseQtImage.copy(QRect(*i))
                # images.append(instance_crop)
                # images.append(instance_crop.scaled(
                #     400, 300, Qt.KeepAspectRatio))
        # print(images)
        self.cur_images = images
        self.changePixmap.emit(images)
        self.frame_signal.emit(self.frame_n)

    def run(self):
        while 1:
            if self.mode == PLAYING:
                if self.frame_n < self.total_frame:
                    self.update_imgage()
                    self.frame_n = self.frame_n + 1
                    time.sleep(0.02)
            else:
                time.sleep(0.20)

    def set_frame(self, frame_d):
        self.frame_n = frame_d
        self.update_imgage()


class InferenceThread(QThread):
    inference_signal = pyqtSignal(int)
    frame_info_signal = pyqtSignal(object)
    classes_signal = pyqtSignal(list)

    def __init__(self, val, parent=None):
        super(InferenceThread, self).__init__(parent)
        self.model = val.model
        # self.total_frame = val.total_frame
        self.dataset = val.dataset
        self.out_dir = val.out_dir

    def run(self):
        print(self.out_dir)
        for frame_info in detect(self.model, self.dataset, self.out_dir):
            # print(frame_info)
            # if type(frame_info) == dict:
            #     if (frame_info['frame'] == 1):
            #         self.inference_signal.emit(INFERENCE_INITIALIZED)
            #     self.frame_info_signal.emit(
            #         [frame_info['frame'], frame_info['bboxes']])
            if type(frame_info) == dict:
                if (frame_info['frame'] == 1):
                    self.inference_signal.emit(INFERENCE_INITIALIZED)
                self.frame_info_signal.emit(frame_info)
            elif type(frame_info) == list:
                self.classes_signal.emit(frame_info)
        self.inference_signal.emit(INFERENCE_FINISHED)


class Ui(QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('main.ui', self)
        self.setStyleSheet(open('stylesheet.css', 'r').read())

        self.imgLabel_0 = self.findChild(QLabel, 'imgLabel_0')
        self.imgLabel_6 = self.findChild(QLabel, 'imgLabel_6')
        self.imgLabel_1 = ClickableLabel(
            self.findChild(QLabel, 'imgLabel_1'), 1)
        self.imgLabel_2 = ClickableLabel(
            self.findChild(QLabel, 'imgLabel_2'), 2)
        self.imgLabel_3 = ClickableLabel(
            self.findChild(QLabel, 'imgLabel_3'), 3)
        self.imgLabel_4 = ClickableLabel(
            self.findChild(QLabel, 'imgLabel_4'), 4)
        self.imgLabel_5 = ClickableLabel(
            self.findChild(QLabel, 'imgLabel_5'), 5)

        # self.imgLabel_1 = self.findChild(QPushButton, 'imgLabel_1')
        # self.imgLabel_2 = self.findChild(QPushButton, 'imgLabel_2')
        # self.imgLabel_3 = self.findChild(QPushButton, 'imgLabel_3')
        # self.imgLabel_4 = self.findChild(QPushButton, 'imgLabel_4')
        # self.imgLabel_5 = self.findChild(QPushButton, 'imgLabel_5')

        self.inference_progress = self.findChild(QLabel, 'inference_progress')
        self.frame_progress = self.findChild(QLabel, 'frame_progress')
        self.total_instances = self.findChild(QLabel, 'total_instances')
        self.current_info_title = self.findChild(QLabel, 'current_info_title')
        self.current_info_label = self.findChild(QLabel, 'current_info_label')
        self.record_status_title = self.findChild(
            QLabel, 'record_status_title')
        self.record_status_label = self.findChild(
            QLabel, 'record_status_label')

        self.STOP = self.findChild(QPushButton, 'STOP')
        self.RECORD = self.findChild(QPushButton, 'RECORD')
        self.pickmodel = self.findChild(QPushButton, 'pickmodel')
        self.pickvideo = self.findChild(QPushButton, 'pickvideo')
        self.startInference = self.findChild(QPushButton, 'startInference')
        self.startInference.setStyleSheet("background-color : yellow")

        self.slider = self.findChild(QSlider, 'slider')
        self.pbar = self.findChild(QProgressBar, 'pbar')
        self.offset_input = self.findChild(QTextEdit, 'offset_input')
        self.offset_label = self.findChild(QLabel, 'offset_label')
        self.actiondark_blue = self.findChild(QAction, 'actiondark_blue')
        # self.actiondark_blue.triggered.connect(self.changeStyle('dark_blue.xml'))
        self.actiondark_blue.triggered.connect(self.changeStyle)
        apply_stylesheet(self, list_themes()[1])
        # 1 14 15
        # self.pbar.setStyle("background-color: red")
        self.show()

    def changeStyle(self):
        apply_stylesheet(self, 'dark_blue.xml')


class MainWindow(QMainWindow):
    # class constructor

    def __init__(self):
        # call QWidget constructor
        super().__init__()
        self.ui = Ui()

        self.total_frame = 0
        self.frame_n = 1
        self.instances = {}
        self.frame_infos = {}

        # default offset
        self.offset = 10000
        self.mode = STOPPED
        self.inference_status = UNINITIALIZED
        self.out_dir = 'inference/output/video'
        self.model = '/home/edgar/Desktop/yolov5/best.pt'
        self.inputVideo = '/home/edgar/Desktop/yolov5/Video6.mp4'
        self.magni = 1
        self.stats = {'total_instances': 0}

        self.th = VideoThread(self)
        self.th.start()
        self.ui.STOP.clicked.connect(self.StopClicked)
        self.ui.slider.valueChanged.connect(self.setFrame)
        self.ui.PLAY.clicked.connect(self.PlayClicked)
        self.ui.RECORD.clicked.connect(self.RecordClicked)
        self.ui.pickmodel.clicked.connect(self.setModel)
        self.ui.pickvideo.clicked.connect(self.setInputVideo)
        self.ui.startInference.clicked.connect(self.startInference)
        self.th.changePixmap.connect(self.setImage)

        self.th.frame_signal.connect(self.updateSlideer)
        self.ui.imgLabel_1.clicked.connect(self.instance_clicked)
        self.ui.imgLabel_2.clicked.connect(self.instance_clicked)
        self.ui.imgLabel_3.clicked.connect(self.instance_clicked)
        self.ui.imgLabel_4.clicked.connect(self.instance_clicked)
        self.ui.imgLabel_5.clicked.connect(self.instance_clicked)
        self.ui.offset_input.textChanged.connect(self.offset_input)

        self.ui.actiondark_blue.trigger

        # self.ui.rbtn1.clicked.connect(self.radio_clicked)
        # self.ui.rbtn2.clicked.connect(self.radio_clicked)
        # self.ui.rbtn3.clicked.connect(self.radio_clicked)
        # self.ui.imgLabel_1.mousePressEvent = self.instance_clicked

    def startInference(self):
        click_sound.play()
        if self.inference_status == UNINITIALIZED:
            self.dataset = LoadImages(
                self.inputVideo, self.offset, img_size=640, stride=32)
            self.total_frame = self.dataset.nframes - self.offset
            self.th.total_frame = self.total_frame
            self.ui.slider.setMaximum(self.total_frame)
            self.inference = InferenceThread(self)
            self.inference.inference_signal.connect(self.updateInferenceStatus)
            self.inference.frame_info_signal.connect(self.addFrameInfo)
            self.inference.classes_signal.connect(self.updateCls)
            self.inference_status = INFERENCE_INITIALIZED
            self.inference.start()

    # @pyqtSlot(list)

    @pyqtSlot(object)
    def addFrameInfo(self, frame_info):
        # self.th.frame_infos[cur_frame] = frame_info[1]
        cur_frame = frame_info['frame']
        progress = f"{cur_frame/self.total_frame:.2%}"
        self.ui.frame_progress.setText(
            f'<b style="font-dize: 20px">{progress}</b>  {cur_frame}/{self.total_frame}')
        num_instances = frame_info['total_instance']
        self.ui.pbar.setValue(int(float(progress[:-1])))
        if num_instances:
            # self.th.frame_infos[cur_frame] = frame_info['instances']
            self.th.instances[cur_frame] = frame_info['instances']
            classes_info = frame_info['classes']
            self.frame_infos[cur_frame] = frame_info['classes']
            self.stats['total_instances'] = self.stats['total_instances'] + \
                num_instances
            total_instances = self.stats['total_instances']
            s = f'Total_Instances: {total_instances}\n'
            # print(frame_info)
            for i in classes_info:
                cls_cnt, avg_cnf = classes_info[i]
                self.stats[i] = [self.stats[i][0] +
                                 cls_cnt, self.stats[i][1] + cls_cnt * avg_cnf]
                s = s + \
                    f"{i}_cnt : {self.stats[i][0]}, avg_conf: {self.stats[i][1] / self.stats[i][0]:.2%}\n"
            self.ui.total_instances.setText(s)

        # print(self.stats)

    @ pyqtSlot(list)
    def updateCls(self, cls):
        self.clsses = cls
        for i in cls:
            self.stats[i] = [0, 0]

    def setModel(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(
            self, "QFileDialog.getOpenFileName()", "", "Checkpoint Files(*.pt | *.pth)", options=options)
        if fileName:
            self.model = fileName
            print(self.model)
            self.ui.pickmodel.setText(fileName.split('/')[-1])

    def setInputVideo(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(
            self, "QFileDialog.getOpenFileName()", "", "MP4(*.mp4);;AVI(*.avi);;MOV(*.mov)", options=options)
        if fileName:
            self.inputVideo = fileName
            print(self.inputVideo)
            showing_filename = fileName.split('/')[-1]
            self.core_videoname = showing_filename[:-4]
            self.out_dir = os.path.join(self.out_dir, self.core_videoname)
            self.th.out_dir = self.out_dir
            self.ui.pickvideo.setText(fileName.split('/')[-1])

    def instance_clicked(self, value):
        print(value)
        self.magni = value
        if (self.mode == STOPPED and self.inference_status != UNINITIALIZED) and value < len(self.th.cur_images):
            self.ui.imgLabel_6.setPixmap(
                QPixmap.fromImage(self.th.cur_images[value]))

    @ pyqtSlot(int)
    def updateSlideer(self, val):
        self.ui.slider.setValue(val)
        if val in self.frame_infos:
            current_frame_data = self.frame_infos[val]
            text = ''
            for i in current_frame_data:
                text += f"{i} count:{current_frame_data[i][0]} / avg_cnf:{current_frame_data[i][1]:.2%}\n"
        else:
            text = 'No Instance'
        self.ui.current_info_label.setText(text)

    @ pyqtSlot(int)
    def updateInferenceStatus(self, status):
        # self.ui.label.setText(status)
        if status == INFERENCE_INITIALIZED:
            print('INFERENCE_INITIALIZED')
            self.ui.PLAY.setStyleSheet("background-color : yellow")
            self.inference_status = INFERENCE_INITIALIZED
            self.ui.inference_progress.setText(
                '<b style="color: blue">Inference Intialized, PLAYABLE</b>')
            self.ui.startInference.setStyleSheet("background-color : ")

        elif status == INFERENCE_FINISHED:
            print('INFERENCE_FINISHED')
            self.ui.PLAY.setStyleSheet("background-color : green")
            self.inference_status = INFERENCE_FINISHED
            self.th.inference_status = INFERENCE_FINISHED
            self.ui.inference_progress.setText(
                f'<b style="color: green">Inference Finished. Total {self.total_frame} f</b>')
            self.ui.RECORD.setStyleSheet("background-color : yellow")
        elif status == RECORD_FINISHED:
            self.ui.RECORD.setStyleSheet("background-color : green")

    def setFrame(self):
        if self.mode == STOPPED and self.inference_status != UNINITIALIZED:
            self.th.set_frame(self.ui.slider.value())

    @ pyqtSlot(list)
    def setImage(self, images):
        for i in range(6):
            if i < len(images):
                eval(
                    f"self.ui.imgLabel_{i}.setPixmap(QPixmap.fromImage(images[{i}]))")
            else:
                eval(f"self.ui.imgLabel_{i}.setText('Instance {i}')")
        if self.magni < len(images):
            eval(
                f"self.ui.imgLabel_6.setPixmap(QPixmap.fromImage(images[{self.magni}]))")

    def offset_input(self):
        if self.ui.offset_input.toPlainText().isdigit():
            self.offset = int(self.ui.offset_input.toPlainText())
            print(self.offset)

    def PlayClicked(self):
        if self.mode != PLAYING and self.inference_status != UNINITIALIZED:
            self.mode = PLAYING
            self.th.mode = PLAYING
        click_sound.play()

    def StopClicked(self):
        self.th.mode = STOPPED
        self.mode = STOPPED
        click_sound.play()

    def RecordClicked(self):
        if self.inference_status == INFERENCE_FINISHED:
            self.incoding_th = IncodingThread(self.out_dir)
            self.incoding_th.start()
            self.incoding_th.record_signal.connect(self.updateInferenceStatus)
            self.incoding_th.record_progress.connect(self.recordStatusUpdate)
        click_sound.play()

    @ pyqtSlot(str)
    def recordStatusUpdate(self, progress_text):
        incoded_frames = int(progress_text[6:12])
        s = f'{incoded_frames/2639:.2%} / '
        self.ui.record_status_label.setText(s + progress_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    click_wav = 'modern.wav'
    click_sound = QtMultimedia.QSoundEffect()
    click_sound.setSource(QUrl.fromLocalFile(click_wav))
    click_sound.setVolume(50)
    mainWindow = MainWindow()

    # mainWindow.show()

    sys.exit(app.exec_())
