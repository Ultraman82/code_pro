#!/usr/bin/env python
# coding: utf-8

import sys
import os
import cv2
import time
import glob

from monitor import detect
from utils.datasets import LoadImages
from PyQt5.QtWidgets import QMainWindow, QApplication, QSlider, QFileDialog
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import QtCore, QtGui, QtWidgets

from collections import deque


buffer = 32

greenLower = (29, 86, 6)
greenUpper = (64, 255, 255)
# greenUpper = (225, 100, 70)

pts = deque(maxlen=buffer)
counter = 0
(dX, dY) = (0, 0)
direction = ""
result_folder = "inference/output/cat"


UNINITIALIZED = 0
INITIALIZED = 1
INFERENCE_INITIALIZED = 2
INFERENCE_FINISHED = 5
PLAYING = 3
STOPPED = 4


class VideoThread(QThread):
    changePixmap = pyqtSignal(QImage)
    frame_signal = pyqtSignal(int)

    def __init__(self, val, parent=None):
        super(VideoThread, self).__init__(parent)
        self.frame_n = 1
        self.total_frame = val.total_frame
        self.mode = val.mode
        self.inference_status = val.inference_status
        self.out_dir = val.out_dir

    def update_imgage(self):
        print(f"frame_n:{self.frame_n}")
        img_path = result_folder + f"/{self.frame_n}.jpg"
        frame = cv2.imread(img_path)
        rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgbImage.shape
        bytesPerLine = ch * w
        convertToQtFormat = QImage(
            rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
        p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
        self.changePixmap.emit(p)
        self.frame_signal.emit(self.frame_n)

    def run(self):
        while 1:
            if self.mode == PLAYING:
                if self.frame_n < self.total_frame:
                    self.update_imgage()
                    self.frame_n = self.frame_n + 1
                    time.sleep(0.02)
            # elif self.inference_status == UNINITIALIZED:
            #     if len(os.listdir(self.out_dir)) == 0:
            #         print('still empty')
            #     else:
            #         print("triggered INFERENCE_INITIALIZED")
            #         self.inference_status = INFERENCE_INITIALIZED
            #         self.inference_signal.emit(INFERENCE_INITIALIZED)
                # time.sleep(0.20)
            else:
                time.sleep(0.20)

            # elif self.inference_status == INFERENCE_INITIALIZED and self.mode == PLAYING:
            #     print("len of the images: ",  len(os.listdir(self.out_dir)))
            #     time.sleep(0.20)

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

    def run(self):
        for i in detect(self.model, self.dataset):
            if i == 0:
                self.inference_signal.emit(INFERENCE_INITIALIZED)
        self.inference_signal.emit(INFERENCE_FINISHED)


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(815, 638)
        self.imgLabel_1 = QtWidgets.QLabel(Dialog)
        self.imgLabel_1.setGeometry(QtCore.QRect(150, 80, 471, 441))
        self.imgLabel_1.setAutoFillBackground(False)
        self.imgLabel_1.setFrameShape(QtWidgets.QFrame.Box)
        self.imgLabel_1.setFrameShadow(QtWidgets.QFrame.Raised)
        self.imgLabel_1.setLineWidth(2)
        self.imgLabel_1.setScaledContents(True)
        self.imgLabel_1.setObjectName("imgLabel_1")
        self.STOP = QtWidgets.QPushButton(Dialog)
        self.STOP.setGeometry(QtCore.QRect(10, 80, 71, 31))
        self.STOP.setObjectName("STOP")

        self.PLAY = QtWidgets.QPushButton(Dialog)
        self.PLAY.setGeometry(QtCore.QRect(10, 120, 131, 51))
        self.PLAY.setObjectName("PLAY")

        self.pickmodel = QtWidgets.QPushButton(Dialog)
        self.pickmodel.setGeometry(QtCore.QRect(10, 10, 100, 60))
        self.pickmodel.setObjectName("pickmodel_button")

        self.pickvideo = QtWidgets.QPushButton(Dialog)
        self.pickvideo.setGeometry(QtCore.QRect(110, 10, 100, 60))
        self.pickvideo.setObjectName("pickvideo_button")

        self.startInference = QtWidgets.QPushButton(Dialog)
        self.startInference.setGeometry(QtCore.QRect(220, 10, 100, 60))
        self.startInference.setObjectName("startInference_button")

        self.imgLabel_3 = QtWidgets.QLabel(Dialog)
        self.imgLabel_3.setGeometry(QtCore.QRect(630, 240, 151, 131))
        self.imgLabel_3.setFrameShape(QtWidgets.QFrame.Box)
        self.imgLabel_3.setFrameShadow(QtWidgets.QFrame.Raised)
        self.imgLabel_3.setLineWidth(2)
        self.imgLabel_3.setScaledContents(True)
        self.imgLabel_3.setObjectName("imgLabel_3")

        # slider
        self.slider = QtWidgets.QSlider(Qt.Horizontal, Dialog)
        self.slider.setObjectName("slider")
        self.slider.setGeometry(QtCore.QRect(150, 520, 471, 50))
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(20)
        self.slider.setSingleStep(5)
        self.slider.setValue(1)
        self.slider.setMaximum(500)
        self.slider.setMinimum(1)

        self.TEXT_2 = QtWidgets.QTextBrowser(Dialog)
        self.TEXT_2.setGeometry(QtCore.QRect(10, 210, 131, 31))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.TEXT_2.setFont(font)
        self.TEXT_2.setObjectName("TEXT_2")
        self.TEXT_3 = QtWidgets.QTextBrowser(Dialog)
        self.TEXT_3.setGeometry(QtCore.QRect(10, 270, 101, 31))
        self.TEXT_3.setObjectName("TEXT_3")
        self.TEXT_4 = QtWidgets.QTextBrowser(Dialog)
        self.TEXT_4.setGeometry(QtCore.QRect(10, 310, 101, 31))
        self.TEXT_4.setObjectName("TEXT_4")
        self.TEXT_5 = QtWidgets.QTextBrowser(Dialog)
        self.TEXT_5.setGeometry(QtCore.QRect(10, 350, 101, 31))
        self.TEXT_5.setObjectName("TEXT_5")
        self.TEXT_6 = QtWidgets.QTextBrowser(Dialog)
        self.TEXT_6.setGeometry(QtCore.QRect(90, 80, 51, 31))
        self.TEXT_6.setObjectName("TEXT_6")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(20, 189, 111, 21))

        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate(
            "Dialog", "CodePro Monitoring System"))
        self.imgLabel_1.setText(_translate("Dialog", "IMG1"))
        self.STOP.setText(_translate("Dialog", "STOP"))
        self.PLAY.setText(_translate("Dialog", "PLAY"))
        self.pickmodel.setText(_translate("Dialog", "Pick Model"))
        self.pickvideo.setText(_translate("Dialog", "Pick Video"))
        self.startInference.setText(_translate("Dialog", "Start Inference"))

        self.imgLabel_3.setText(_translate("Dialog", "IMG3"))
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
        self.offset = 100
        self.mode = STOPPED
        self.inference_status = UNINITIALIZED
        self.out_dir = 'inference/output/cat'
        self.model = '/home/edgar/yolov5/best.pt'
        self.inputVideo = '/home/edgar/yolov5/cat-footpush.mp4'

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

    def startInference(self):
        self.dataset = LoadImages(self.inputVideo, self.offset, img_size=640)
        self.total_frame = self.dataset.nframes - self.offset
        self.th.total_frame = self.dataset.nframes - self.offset
        print(self.total_frame)
        self.inference_status = INITIALIZED
        self.inference = InferenceThread(self)
        self.inference.inference_signal.connect(self.updateInferenceStatus)
        self.inference.start()
        # self.updateInferenceStatus("Save Imgages Started")

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
            print(self.inputVideo)
            self.ui.pickvideo.setText(fileName[-15:])

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

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.ui.imgLabel_1.setPixmap(QPixmap.fromImage(image))
        for i in os.listdir(self.out_dir + f"/{self.frame_n}"):
            print(i)

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
