#!/usr/bin/env python
# coding: utf-8

import sys
import os
import cv2
import time
from monitor import detect

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

PLAY = 1
STOP = 0
STARTED = 2


class VideoThread(QThread):
    changePixmap = pyqtSignal(QImage)
    frame_signal = pyqtSignal(int)
    inference_status = pyqtSignal(int)

    def __init__(self, val, parent=None):
        super(VideoThread, self).__init__(parent)
        self.frame_n = 1
        self.video_len = 506
        self.mode = STOP
        self.out_dir = val.out_dir

    def update_imgage(self):
        print(f"frame_n:{self.frame_n}")
        img_path = result_folder + f"/{(self.frame_n)}.jpg"
        frame = cv2.imread(img_path)
        rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgbImage.shape
        bytesPerLine = ch * w
        convertToQtFormat = QImage(
            rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
        p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
        self.changePixmap.emit(p)
        self.frame_signal.emit(self.frame_n)

    def checkInferenceStarted(self):
        while len(os.listdir(self.out_dir)) == 0:
            print("still empty")
            time.sleep(0.2)
        self.inference_status.emit(STARTED)

    def run(self):
        if self.mode == PLAY:
            while self.frame_n < self.video_len:
                if self.mode == STOP:
                    break
                self.update_imgage()
                self.frame_n = self.frame_n + 1
                time.sleep(0.020)
        elif self.mode == STOP:
            self.checkInferenceStarted()

    def set_frame(self, frame_d):
        self.frame_n = frame_d
        self.update_imgage()


class InferenceThread(QThread):
    # inference_status = pyqtSignal(str)

    def __init__(self, val, parent=None):
        super(InferenceThread, self).__init__(parent)
        self.model = val.model
        self.input = val.inputVideo
        self.status = STOP
        self.out_dir = val.out_dir
        print(val.model)

    def run(self):
        self.total_frame = detect(self.model, self.input)
        # self.inference_status.emit("INFERENCE_DONE")


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

        # self.th.start()

        self.logic = 0
        self.frame_n = 1
        self.length = 506
        self.mode = STOP
        self.inference_status = None
        self.out_dir = 'inference/output/cat'
        self.th = VideoThread(self)

        self.ui.STOP.clicked.connect(self.StopClicked)
        self.ui.slider.valueChanged.connect(self.setFrame)
        self.ui.PLAY.clicked.connect(self.PlayClicked)
        self.ui.pickmodel.clicked.connect(self.setModel)
        self.ui.pickvideo.clicked.connect(self.setInputVideo)
        self.ui.startInference.clicked.connect(self.startInference)
        # self.ui.startInference.clicked.connect(self.updateInferenceStatus)
        # self.openFileNameDialog()

    def startInference(self):
        self.inference = InferenceThread(self)
        self.inference.start()
        self.th.start()
        self.th.inference_status.connect(self.updateInferenceStatus)

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
        if status == STARTED:
            self.ui.PLAY.setStyleSheet("background-color : green")
            self.inference_status = STARTED

    def setFrame(self):
        if self.mode == STOP:
            self.th.set_frame(self.ui.slider.value())

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.ui.imgLabel_1.setPixmap(QPixmap.fromImage(image))

    def PlayClicked(self):
        print(self.th.inference_status)
        if self.mode != PLAY and self.inference_status == STARTED:
            self.mode = PLAY
            self.th.mode = PLAY
            self.th.changePixmap.connect(self.setImage)
            self.th.frame_signal.connect(self.updateSlideer)
            self.th.start()

    def StopClicked(self):
        self.th.mode = STOP
        self.mode = STOP


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # create and show mainWindow
    mainWindow = MainWindow()
    mainWindow.show()

    sys.exit(app.exec_())
