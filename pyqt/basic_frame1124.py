#!/usr/bin/env python
# coding: utf-8

import sys
import os
import cv2
import time

from monitor import detect
from utils.datasets import LoadImages
from PyQt5.QtWidgets import QMainWindow, QApplication, QSlider, QFileDialog, QRadioButton, QLabel, QPushButton, QFrame, QTextBrowser
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot, QRect, QMetaObject, QCoreApplication
from PyQt5.QtGui import QImage, QPixmap, QFont

from collections import deque

buffer = 32

greenLower = (29, 86, 6)
greenUpper = (64, 255, 255)
# greenUpper = (225, 100, 70)

pts = deque(maxlen=buffer)
counter = 0
(dX, dY) = (0, 0)
direction = ""

UNINITIALIZED = 0
INITIALIZED = 1
INFERENCE_INITIALIZED = 2
INFERENCE_FINISHED = 5
PLAYING = 3
STOPPED = 4


class ClickableLabel(QLabel):
    clicked = pyqtSignal(int)

    def __init__(self, parent=None, id=0):
        QLabel.__init__(self, parent)
        self.id = id
        print(id)

    def mousePressEvent(self, event):
        self.clicked.emit(self.id)
        super(ClickableLabel, self).mousePressEvent(event)


class VideoThread(QThread):
    changePixmap = pyqtSignal(list)
    frame_signal = pyqtSignal(int)

    def __init__(self, val, parent=None):
        super(VideoThread, self).__init__(parent)
        self.frame_n = 1
        self.frame_infos = {}
        self.total_frame = val.total_frame
        self.instance_cls = val.instance_cls
        self.mode = val.mode
        self.inference_status = val.inference_status
        self.out_dir = val.out_dir

    def convert2qtimage(self, img_path):
        frame = cv2.imread(img_path)
        rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgbImage.shape
        bytesPerLine = ch * w
        convertToQtFormat = QImage(
            rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
        p = convertToQtFormat.scaled(1280, 720, Qt.KeepAspectRatio)
        return p

    def update_imgage(self):
        # print(f"frame_n:{self.frame_n}")
        img = self.out_dir + f"/{self.frame_n}.jpg"
        frame = cv2.imread(img)
        rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgbImage.shape
        bytesPerLine = ch * w
        baseQtImage = QImage(
            rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)

        images = [baseQtImage.scaled(1920, 1080, Qt.KeepAspectRatio)]
        if self.frame_n in self.frame_infos:
            frame_data = self.frame_infos[self.frame_n]
            for i in frame_data:
                # print(i)
                instance_crop = baseQtImage.copy(QRect(*i))
                # images.append(instance_crop)
                images.append(instance_crop.scaled(
                    640, 480, Qt.KeepAspectRatio))
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
    frame_info_signal = pyqtSignal(list)

    def __init__(self, val, parent=None):
        super(InferenceThread, self).__init__(parent)
        self.model = val.model
        # self.total_frame = val.total_frame
        self.dataset = val.dataset
        self.out_dir = val.out_dir

    def run(self):
        for i, frame_info in detect(self.model, self.dataset, self.out_dir):
            if i == 0:
                self.inference_signal.emit(INFERENCE_INITIALIZED)
            if len(frame_info) != 0:
                self.frame_info_signal.emit([i, frame_info])
        self.inference_signal.emit(INFERENCE_FINISHED)


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1920, 1080)
        self.imgLabel_0 = QLabel(Dialog)
        self.imgLabel_0.setGeometry(QRect(150, 80, 1000, 720))
        self.imgLabel_0.setAutoFillBackground(False)
        self.imgLabel_0.setFrameShape(QFrame.Box)
        self.imgLabel_0.setFrameShadow(QFrame.Raised)
        self.imgLabel_0.setLineWidth(2)
        self.imgLabel_0.setScaledContents(True)
        self.imgLabel_0.setObjectName("imgLabel_0")

        self.imgLabel_6 = QLabel(Dialog)
        self.imgLabel_6.setGeometry(QRect(1200, 80, 640, 480))
        self.imgLabel_6.setAutoFillBackground(False)
        self.imgLabel_6.setFrameShape(QFrame.Box)
        self.imgLabel_6.setFrameShadow(QFrame.Raised)
        self.imgLabel_6.setLineWidth(2)
        # self.imgLabel_6.setScaledContents(True)
        self.imgLabel_6.setObjectName("MAGNIFIED_IMAGE")

        self.STOP = QPushButton(Dialog)
        self.STOP.setGeometry(QRect(10, 80, 71, 31))
        self.STOP.setObjectName("STOP")

        self.PLAY = QPushButton(Dialog)
        self.PLAY.setGeometry(QRect(10, 120, 131, 51))
        self.PLAY.setObjectName("PLAY")

        self.pickmodel = QPushButton(Dialog)
        self.pickmodel.setGeometry(QRect(10, 10, 100, 60))
        self.pickmodel.setObjectName("pickmodel_button")

        self.pickvideo = QPushButton(Dialog)
        self.pickvideo.setGeometry(QRect(110, 10, 100, 60))
        self.pickvideo.setObjectName("pickvideo_button")

        self.startInference = QPushButton(Dialog)
        self.startInference.setGeometry(QRect(220, 10, 100, 60))
        self.startInference.setObjectName("startInference_button")

        self.imgLabel_1 = ClickableLabel(Dialog, 1)
        self.imgLabel_1.setGeometry(QRect(150, 900, 100, 100))
        self.imgLabel_1.setFrameShape(QFrame.Box)
        self.imgLabel_1.setFrameShadow(QFrame.Raised)
        self.imgLabel_1.setLineWidth(2)
        self.imgLabel_1.setScaledContents(True)
        self.imgLabel_1.setObjectName("imgLabel_1")
        self.imgLabel_1.setNum(1.0)

        self.imgLabel_2 = ClickableLabel(Dialog, 2)
        self.imgLabel_2.setGeometry(QRect(250, 900, 100, 100))
        self.imgLabel_2.setFrameShape(QFrame.Box)
        self.imgLabel_2.setFrameShadow(QFrame.Raised)
        self.imgLabel_2.setLineWidth(2)
        self.imgLabel_2.setScaledContents(True)
        self.imgLabel_2.setObjectName("imgLabel_2")

        self.imgLabel_3 = ClickableLabel(Dialog, 3)
        self.imgLabel_3.setGeometry(QRect(350, 900, 100, 100))
        self.imgLabel_3.setFrameShape(QFrame.Box)
        self.imgLabel_3.setFrameShadow(QFrame.Raised)
        self.imgLabel_3.setLineWidth(2)
        self.imgLabel_3.setScaledContents(True)
        self.imgLabel_3.setObjectName("imgLabel_3")

        self.imgLabel_4 = ClickableLabel(Dialog, 4)
        self.imgLabel_4.setGeometry(QRect(450, 900, 100, 100))
        self.imgLabel_4.setFrameShape(QFrame.Box)
        self.imgLabel_4.setFrameShadow(QFrame.Raised)
        self.imgLabel_4.setLineWidth(2)
        self.imgLabel_4.setScaledContents(True)
        self.imgLabel_4.setObjectName("imgLabel_4")

        self.imgLabel_5 = ClickableLabel(Dialog, 5)
        self.imgLabel_5.setGeometry(QRect(550, 900, 100, 100))
        self.imgLabel_5.setFrameShape(QFrame.Box)
        self.imgLabel_5.setFrameShadow(QFrame.Raised)
        self.imgLabel_5.setLineWidth(2)
        self.imgLabel_5.setScaledContents(True)
        self.imgLabel_5.setObjectName("imgLabel_5")

        # slider
        self.slider = QSlider(Qt.Horizontal, Dialog)
        self.slider.setObjectName("slider")
        self.slider.setGeometry(QRect(150, 800, 1000, 50))
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(20)
        self.slider.setSingleStep(5)
        self.slider.setValue(1)
        self.slider.setMaximum(500)
        self.slider.setMinimum(1)

        # self.rbtn1 = QRadioButton('First Button', Dialog)
        # self.rbtn1.move(50, 750)
        # self.rbtn1.setChecked(True)

        # self.rbtn2 = QRadioButton('Second Button', Dialog)
        # self.rbtn2.move(50, 850)
        # self.rbtn2.setChecked(False)

        # self.rbtn3 = QRadioButton('Third Button', Dialog)
        # self.rbtn3.move(50, 950)
        # self.rbtn3.setChecked(False)

        self.TEXT_2 = QTextBrowser(Dialog)
        self.TEXT_2.setGeometry(QRect(10, 210, 131, 31))
        font = QFont()
        font.setPointSize(9)
        self.label = QLabel(Dialog)
        self.label.setGeometry(QRect(20, 189, 111, 21))
        font = QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.retranslateUi(Dialog)
        QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QCoreApplication.translate
        Dialog.setWindowTitle(_translate(
            "Dialog", "CodePro Monitoring System"))
        self.imgLabel_0.setText(_translate("Dialog", "MAIN_IMAGE"))
        self.imgLabel_1.setText(_translate("Dialog", "INSTANCE1"))
        self.imgLabel_2.setText(_translate("Dialog", "INSTANCE2"))
        self.imgLabel_3.setText(_translate("Dialog", "INSTANCE3"))
        self.imgLabel_4.setText(_translate("Dialog", "INSTANCE4"))
        self.imgLabel_5.setText(_translate("Dialog", "INSTANCE5"))
        self.imgLabel_6.setText(_translate("Dialog", "MAGNIFIED_IMAGE"))

        self.STOP.setText(_translate("Dialog", "STOP"))
        self.PLAY.setText(_translate("Dialog", "PLAY"))
        self.pickmodel.setText(_translate("Dialog", "Pick Model"))
        self.pickvideo.setText(_translate("Dialog", "Pick Video"))
        self.startInference.setText(_translate("Dialog", "Start Inference"))
        # self.rbtn1.setText(_translate("Dialog", "CLASS1"))
        # self.rbtn2.setText(_translate("Dialog", "CLASS2"))
        # self.rbtn3.setText(_translate("Dialog", "CLASS3"))
        self.label.setText(_translate("Dialog", "Center Coordinate"))


class MainWindow(QMainWindow):
    # class constructor

    def __init__(self):
        # call QWidget constructor
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.total_frame = 0
        self.frame_n = 1
        self.frame_infos = {}
        self.offset = 10000
        self.mode = STOPPED
        self.inference_status = UNINITIALIZED
        self.out_dir = 'inference/output/video'
        self.model = '/home/edgar/Desktop/yolov5/best.pt'
        self.inputVideo = '/home/edgar/Desktop/yolov5/Video6.mp4'
        self.magni = 1

        self.instance_cls = 0
        self.th = VideoThread(self)
        self.th.start()
        self.ui.STOP.clicked.connect(self.StopClicked)
        self.ui.slider.valueChanged.connect(self.setFrame)
        self.ui.PLAY.clicked.connect(self.PlayClicked)
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
        # self.ui.rbtn1.clicked.connect(self.radio_clicked)
        # self.ui.rbtn2.clicked.connect(self.radio_clicked)
        # self.ui.rbtn3.clicked.connect(self.radio_clicked)
        # self.ui.imgLabel_1.mousePressEvent = self.instance_clicked
        # self.ui.imgLabel_1.connect(self.QPLabel, pyqtSignal(
        #     _fromUtf8("clicked()")), self.doSomething)

    def startInference(self):
        self.dataset = LoadImages(
            self.inputVideo, self.offset, img_size=640, stride=32)
        self.total_frame = self.dataset.nframes - self.offset
        self.th.total_frame = self.dataset.nframes - self.offset
        self.ui.slider.setMaximum(self.total_frame)
        self.inference_status = INITIALIZED
        self.inference = InferenceThread(self)
        self.inference.inference_signal.connect(self.updateInferenceStatus)
        self.inference.frame_info_signal.connect(self.addFrameInfo)
        self.inference.start()

    def setModel(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(
            self, "QFileDialog.getOpenFileName()", "", "Checkpoint Files(*.pt | *.pth)", options=options)
        if fileName:
            self.model = fileName
            print(self.model)
            self.ui.pickmodel.setText(fileName[-15:])

    def setInputVideo(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(
            self, "QFileDialog.getOpenFileName()", "", "MP4(*.mp4);;AVI(*.avi);;MOV(*.mov)", options=options)
        if fileName:
            self.inputVideo = fileName
            showing_filename = fileName.split('/')[-1]
            self.core_videoname = showing_filename[:-4]
            self.out_dir = os.path.join(self.out_dir, self.core_videoname)
            self.th.out_dir = self.out_dir
            self.ui.pickvideo.setText(fileName.split('/')[-1])

    # def radio_clicked(self):
    #     if self.ui.rbtn1.isChecked():
    #         self.cls = 0
    #         print("GroupBox_rad1 Chekced")
    #     elif self.ui.rbtn2.isChecked():
    #         self.cls = 1
    #         print("GroupBox_rad2 Checked")
    #     elif self.ui.rbtn3.isChecked():
    #         self.cls = 2
    #         print("GroupBox_rad3 Checked")

    def instance_clicked(self, value):
        self.magni = value
        if (self.mode == STOPPED and self.inference_status != UNINITIALIZED) and value < len(self.th.cur_images):
            self.ui.imgLabel_6.setPixmap(
                QPixmap.fromImage(self.th.cur_images[value]))

    @pyqtSlot(int)
    def updateSlideer(self, val):
        self.ui.slider.setValue(val)

    @pyqtSlot(int)
    def updateInferenceStatus(self, status):
        # self.ui.label.setText(status)
        if status == INFERENCE_INITIALIZED:
            print('INFERENCE_INITIALIZED')
            self.ui.PLAY.setStyleSheet("background-color : yellow")
            self.inference_status = INFERENCE_INITIALIZED
        elif status == INFERENCE_FINISHED:
            print('INFERENCE_FINISHED')
            self.ui.PLAY.setStyleSheet("background-color : green")
            self.inference_status = INFERENCE_FINISHED
            self.th.inference_status = INFERENCE_FINISHED

    @pyqtSlot(int)
    def updateTotalFrame(self, total_frame):
        print('totalFrame updated:', total_frame)
        self.totalFrame = total_frame

    def setFrame(self):
        if self.mode == STOPPED:
            self.th.set_frame(self.ui.slider.value())

    @pyqtSlot(list)
    def setImage(self, images):
        for i in range(6):
            if i < len(images):
                eval(
                    f"self.ui.imgLabel_{i}.setPixmap(QPixmap.fromImage(images[{i}]))")
            else:
                eval(f"self.ui.imgLabel_{i}.setText('EMPTY')")
        if self.magni < len(images):
            eval(
                f"self.ui.imgLabel_6.setPixmap(QPixmap.fromImage(images[{self.magni}]))")

    @pyqtSlot(list)
    def addFrameInfo(self, frame_info):
        self.th.frame_infos[frame_info[0]+1] = frame_info[1]

    def PlayClicked(self):
        print(self.inference_status)
        print(self.mode)
        print("play clicked")
        if self.mode != PLAYING and self.inference_status != UNINITIALIZED:
            self.mode = PLAYING
            self.th.mode = PLAYING

    def StopClicked(self):
        self.th.mode = STOPPED
        self.mode = STOPPED


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # create and show mainWindow
    mainWindow = MainWindow()
    mainWindow.show()

    sys.exit(app.exec_())
