#!/usr/bin/env python
# coding: utf-8

import sys
import os
import cv2
import time

from monitor import detect
from utils.datasets import LoadImages
from PyQt5.QtWidgets import QMainWindow, QApplication, QSlider, QFileDialog, QRadioButton, QLabel, QPushButton, QFrame, QTextBrowser
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot, QRect
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5 import QtCore, QtGui
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
    clicked = pyqtSignal(str)

    def mousePressEvent(self, event):
        self.clicked.emit(self.text())
        super(ClickableLabel, self).mousePressEvent(event)


class VideoThread(QThread):
    changePixmap = pyqtSignal(list)
    frame_signal = pyqtSignal(int)

    def __init__(self, val, parent=None):
        super(VideoThread, self).__init__(parent)
        self.frame_n = 1
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
        p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
        return p

    def update_imgage(self):
        # print(f"frame_n:{self.frame_n}")
        img_core = self.out_dir + f"/{self.frame_n}"
        images = [self.convert2qtimage(img_core + ".jpg")]
        test_path = f"{img_core}/ship 0.jpg"
        if os.path.isfile(test_path):
            images.append(self.convert2qtimage(test_path))
        # for i in range()
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
        self.inference_signal.emit(INFERENCE_FINISHED)


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1920, 1080)
        self.imgLabel_1 = QLabel(Dialog)
        self.imgLabel_1.setGeometry(QRect(150, 80, 1000, 720))
        self.imgLabel_1.setAutoFillBackground(False)
        self.imgLabel_1.setFrameShape(QFrame.Box)
        self.imgLabel_1.setFrameShadow(QFrame.Raised)
        self.imgLabel_1.setLineWidth(2)
        self.imgLabel_1.setScaledContents(True)
        self.imgLabel_1.setObjectName("imgLabel_1")

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

        # self.instance_image_0 = QPushButton(Dialog)
        # self.instance_image_0.setGeometry(QRect(150, 900, 100, 100))
        # self.instance_image_0.setObjectName("instance_image_0")
        # self.instance_image_0.setIcon(QtGui.QIcon('test.jpg'))
        # self.instance_image_0.setIconSize(QtCore.QSize(200, 200))

        self.instance_image_0 = ClickableLabel(Dialog)
        self.instance_image_0.setGeometry(QRect(150, 900, 100, 100))
        self.instance_image_0.setFrameShape(QFrame.Box)
        self.instance_image_0.setFrameShadow(QFrame.Raised)
        self.instance_image_0.setLineWidth(2)
        self.instance_image_0.setScaledContents(True)
        self.instance_image_0.setObjectName("instance_image_0")

        # self.instance_image_1 = QLabel(Dialog)
        # self.instance_image_1.setGeometry(QRect(250, 900, 100, 100))
        # self.instance_image_1.setFrameShape(QFrame.Box)
        # self.instance_image_1.setFrameShadow(QFrame.Raised)
        # self.instance_image_1.setLineWidth(2)
        # self.instance_image_1.setScaledContents(True)
        # self.instance_image_1.setObjectName("instance_image_3")

        # self.instance_image_2 = QLabel(Dialog)
        # self.instance_image_2.setGeometry(QRect(350, 900, 100, 100))
        # self.instance_image_2.setFrameShape(QFrame.Box)
        # self.instance_image_2.setFrameShadow(QFrame.Raised)
        # self.instance_image_2.setLineWidth(2)
        # self.instance_image_2.setScaledContents(True)
        # self.instance_image_2.setObjectName("instance_image_3")

        # self.instance_image_3 = QLabel(Dialog)
        # self.instance_image_3.setGeometry(QRect(450, 900, 100, 100))
        # self.instance_image_3.setFrameShape(QFrame.Box)
        # self.instance_image_3.setFrameShadow(QFrame.Raised)
        # self.instance_image_3.setLineWidth(2)
        # self.instance_image_3.setScaledContents(True)
        # self.instance_image_3.setObjectName("instance_image_3")

        # self.instance_image_4 = QLabel(Dialog)
        # self.instance_image_4.setGeometry(QRect(550, 900, 100, 100))
        # self.instance_image_4.setFrameShape(QFrame.Box)
        # self.instance_image_4.setFrameShadow(QFrame.Raised)
        # self.instance_image_4.setLineWidth(2)
        # self.instance_image_4.setScaledContents(True)
        # self.instance_image_4.setObjectName("instance_image_4")

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

        self.rbtn1 = QRadioButton('First Button', Dialog)
        self.rbtn1.move(50, 750)
        self.rbtn1.setChecked(True)

        self.rbtn2 = QRadioButton('Second Button', Dialog)
        self.rbtn2.move(50, 850)
        self.rbtn2.setChecked(False)

        self.rbtn3 = QRadioButton('Third Button', Dialog)
        self.rbtn3.move(50, 950)
        self.rbtn3.setChecked(False)

        self.TEXT_2 = QTextBrowser(Dialog)
        self.TEXT_2.setGeometry(QRect(10, 210, 131, 31))
        font = QtGui.QFont()
        font.setPointSize(9)
        # self.TEXT_2.setFont(font)
        # self.TEXT_2.setObjectName("TEXT_2")
        # self.TEXT_3 = QtWidgets.QTextBrowser(Dialog)
        # self.TEXT_3.setGeometry(QRect(10, 270, 101, 31))
        # self.TEXT_3.setObjectName("TEXT_3")
        # self.TEXT_4 = QtWidgets.QTextBrowser(Dialog)
        # self.TEXT_4.setGeometry(QRect(10, 310, 101, 31))
        # self.TEXT_4.setObjectName("TEXT_4")
        # self.TEXT_5 = QtWidgets.QTextBrowser(Dialog)
        # self.TEXT_5.setGeometry(QRect(10, 350, 101, 31))
        # self.TEXT_5.setObjectName("TEXT_5")
        # self.TEXT_6 = QtWidgets.QTextBrowser(Dialog)
        # self.TEXT_6.setGeometry(QRect(90, 80, 51, 31))
        # self.TEXT_6.setObjectName("TEXT_6")
        self.label = QLabel(Dialog)
        self.label.setGeometry(QRect(20, 189, 111, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        # QtCore.QObject.connect(self.QPLabel, QtCore.SIGNAL(_fromUtf8("clicked()")), self.doSomething)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate(
            "Dialog", "CodePro Monitoring System"))
        self.imgLabel_1.setText(_translate("Dialog", "IMG1"))
        self.instance_image_0.setText(_translate("Dialog", "0"))
        # self.instance_image_1.setText(_translate("Dialog", "INSTANCE1"))
        # self.instance_image_2.setText(_translate("Dialog", "INSTANCE2"))
        # self.instance_image_3.setText(_translate("Dialog", "INSTANCE3"))
        # self.instance_image_4.setText(_translate("Dialog", "INSTANCE4"))

        self.STOP.setText(_translate("Dialog", "STOP"))
        self.PLAY.setText(_translate("Dialog", "PLAY"))
        self.pickmodel.setText(_translate("Dialog", "Pick Model"))
        self.pickvideo.setText(_translate("Dialog", "Pick Video"))
        self.startInference.setText(_translate("Dialog", "Start Inference"))
        self.rbtn1.setText(_translate("Dialog", "CLASS1"))
        self.rbtn2.setText(_translate("Dialog", "CLASS2"))
        self.rbtn3.setText(_translate("Dialog", "CLASS3"))

        # self.imgLabel_3.setText(_translate("Dialog", "IMG3"))
        # self.slider.setText(_translate("Dialog", "slider"))
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
        self.offset = 10000
        self.mode = STOPPED
        self.inference_status = UNINITIALIZED
        self.out_dir = 'inference/output/video'
        # self.model = '/home/edgar/Desktop/yolov5/runs/train/20211118선용품_video0and1/weights/best.pt'
        # self.model = '/home/edgar/Desktop/yolov5/runs/train/211122_항만감시/weights/best.pt'
        self.model = '/home/edgar/Desktop/yolov5/best.pt'
        self.inputVideo = '/home/edgar/Desktop/yolov5/Video6.mp4'

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
        self.ui.rbtn1.clicked.connect(self.radio_clicked)
        self.ui.rbtn2.clicked.connect(self.radio_clicked)
        self.ui.rbtn3.clicked.connect(self.radio_clicked)
        self.ui.instance_image_0.clicked.connect(self.instance_clicked)
        # self.ui.instance_image_0.mousePressEvent = self.instance_clicked
        # self.ui.instance_image_0.connect(self.QPLabel, pyqtSignal(
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

    def radio_clicked(self):
        if self.ui.rbtn1.isChecked():
            self.cls = 0
            print("GroupBox_rad1 Chekced")
        elif self.ui.rbtn2.isChecked():
            self.cls = 1
            print("GroupBox_rad2 Checked")
        elif self.ui.rbtn3.isChecked():
            self.cls = 2
            print("GroupBox_rad3 Checked")

    def instance_clicked(self, value):
        print(value)

    @pyqtSlot(int)
    def updateSlideer(self, val):
        self.ui.slider.setValue(val)

    @pyqtSlot(int)
    def updateInferenceStatus(self, status):
        # self.ui.label.setText(status)
        if status == INFERENCE_INITIALIZED:
            print('Statuse updated')
            self.ui.PLAY.setStyleSheet("background-color : yellow")
            self.inference_status = INFERENCE_INITIALIZED
        elif status == INFERENCE_FINISHED:
            print('Statuse updated')
            self.ui.PLAY.setStyleSheet("background-color : green")
            self.inference_status = INFERENCE_FINISHED

    @pyqtSlot(int)
    def updateTotalFrame(self, total_frame):
        print('totalFrame updated:', total_frame)
        self.totalFrame = total_frame

    def setFrame(self):
        if self.mode == STOPPED:
            self.th.set_frame(self.ui.slider.value())

    @pyqtSlot(list)
    def setImage(self, images):
        self.ui.imgLabel_1.setPixmap(QPixmap.fromImage(images[0]))
        if len(images) > 1:
            self.ui.instance_image_0.setPixmap(QPixmap.fromImage(images[1]))

        # self.ui.instance_image_0.setPixmap(QPixmap.fromImage(image))
        # for i in os.listdir(self.out_dir + f"/{self.frame_n}"):
        #     print(i)

    def PlayClicked(self):
        print(self.inference_status)
        print(self.mode)
        print("play clicked")
        if self.mode != PLAYING and self.inference_status == INFERENCE_INITIALIZED:
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
