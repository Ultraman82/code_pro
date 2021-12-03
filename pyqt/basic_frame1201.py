#!/usr/bin/env python
# coding: utf-8

import sys
import os
import cv2
import time
import glob
import subprocess

from monitor import detect, LoadImages
from PyQt5.QtWidgets import QMainWindow, QApplication, QSlider, QFileDialog, QLabel, QPushButton, QFrame, QTextEdit, QProgressBar
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
RECORD_FINISHED = 6
PLAYING = 3
STOPPED = 4


class ClickableLabel(QLabel):
    clicked = pyqtSignal(int)

    def __init__(self, parent=None, id=0):
        QLabel.__init__(self, parent)
        self.id = id

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


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1920, 1080)
        font = QFont()
        font.setPointSize(15)

        self.imgLabel_0 = QLabel(Dialog)
        self.imgLabel_0.setGeometry(QRect(150, 80, 1280, 720))
        self.imgLabel_0.setAutoFillBackground(False)
        self.imgLabel_0.setFrameShape(QFrame.Box)
        self.imgLabel_0.setFrameShadow(QFrame.Raised)
        self.imgLabel_0.setLineWidth(2)
        self.imgLabel_0.setScaledContents(True)
        self.imgLabel_0.setObjectName("imgLabel_0")

        # self.le = QLineEdit(Dialog)
        # self.le.returnPressed.connect(self.append_text)
        self.inference_progress = QLabel(Dialog)
        self.inference_progress.setGeometry(QRect(1450, 80, 640, 50))
        self.inference_progress.setFont(font)
        self.inference_progress.setText(
            '<b style="color: red">Inference Unintialized</b>')

        self.frame_progress = QLabel(Dialog)
        self.frame_progress.setGeometry(QRect(1450, 120, 200, 50))
        self.frame_progress.setFont(font)
        self.frame_progress.setText('0 / 0')
        # self.frame_progress.setStyleSheet()

        self.total_instances = QLabel(Dialog)
        self.total_instances.setGeometry(QRect(1450, 160, 300, 100))
        self.total_instances.setFont(font)
        self.total_instances.setText('UNIN')

        self.current_info_title = QLabel(Dialog)
        self.current_info_title.setGeometry(QRect(1450, 200, 300, 100))
        self.current_info_title.setFont(font)
        self.current_info_title.setText(
            '<b style="color: blue">Current Frame Info</b>')

        self.current_info_label = QLabel(Dialog)
        self.current_info_label.setGeometry(QRect(1450, 240, 300, 100))
        self.current_info_label.setFont(font)
        self.current_info_label.setText(
            '<b style="color: blue">not initilized</b>')

        self.record_status_title = QLabel(Dialog)
        self.record_status_title.setGeometry(QRect(1450, 280, 300, 100))
        self.record_status_title.setFont(font)
        self.record_status_title.setText(
            '<b style="color: green">Record Status</b>')

        self.record_status_label = QLabel(Dialog)
        self.record_status_label.setGeometry(QRect(1450, 300, 300, 100))
        self.record_status_label.setFont(font)
        self.record_status_label.setText('UNIN')
        # self.tb = QTextBrowser(Dialog)
        # self.tb.setAcceptRichText(True)
        # self.tb.setOpenExternalLinks(True)
        # self.tb.setGeometry(QRect(1200, 80, 640, 300))
        # self.tb.append('<p style="color: red">Red</p>')

        self.imgLabel_6 = QLabel(Dialog)
        self.imgLabel_6.setGeometry(QRect(1450, 480, 400, 300))
        self.imgLabel_6.setAutoFillBackground(False)
        self.imgLabel_6.setFrameShape(QFrame.Box)
        self.imgLabel_6.setFrameShadow(QFrame.Raised)
        self.imgLabel_6.setLineWidth(2)
        self.imgLabel_0.setScaledContents(True)
        self.imgLabel_6.setObjectName("MAGNIFIED_IMAGE")

        self.STOP = QPushButton(Dialog)
        self.STOP.setGeometry(QRect(10, 80, 71, 31))
        self.STOP.setObjectName("STOP")

        self.PLAY = QPushButton(Dialog)
        self.PLAY.setGeometry(QRect(10, 120, 131, 51))
        self.PLAY.setObjectName("PLAY")

        self.RECORD = QPushButton(Dialog)
        self.RECORD.setGeometry(QRect(10, 300, 131, 51))
        self.RECORD.setObjectName("RECORD")

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
        self.slider.setGeometry(QRect(150, 820, 1280, 50))
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(20)
        self.slider.setSingleStep(5)
        self.slider.setValue(1)
        self.slider.setMaximum(500)
        self.slider.setMinimum(1)

        self.pbar = QProgressBar(Dialog)
        self.pbar.setGeometry(QRect(150, 815, 1280, 10))
        # QProgressBar {
        #         border: 20px solid black;
        #         border-radius: 10px;
        #         background-color: red;
        #         }

        self.pbar.setStyleSheet("""
                QProgressBar{
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    font-size: 15px
                }
                QProgressBar::chunk {
                    background-color: red;
                    width: 10px;
                    margin: 1px;
                }
            """)

        # self.rbtn1 = QRadioButton('First Button', Dialog)
        # self.rbtn1.move(50, 750)
        # self.rbtn1.setChecked(True)

        # self.rbtn2 = QRadioButton('Second Button', Dialog)
        # self.rbtn2.move(50, 850)
        # self.rbtn2.setChecked(False)

        # self.rbtn3 = QRadioButton('Third Button', Dialog)
        # self.rbtn3.move(50, 950)
        # self.rbtn3.setChecked(False)

        self.offset_input = QTextEdit(Dialog)
        self.offset_input.setGeometry(QRect(10, 210, 131, 31))
        self.offset_input.setAcceptRichText(False)
        self.offset_label = QLabel(Dialog)
        self.offset_label.setGeometry(QRect(20, 189, 111, 21))
        # self.offset_label.setFont(font)
        self.offset_label.setObjectName("offset")
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
        self.RECORD.setText(_translate("Dialog", "RECORD"))
        self.pickmodel.setText(_translate("Dialog", "Pick Model"))
        self.pickvideo.setText(_translate("Dialog", "Pick Video"))
        self.startInference.setText(_translate("Dialog", "Start Inference"))
        self.offset_label.setText(_translate(
            "Dialog", "Offset:skipping frames"))
        self.offset_input.setText(_translate("Dialog", "1000"))


class MainWindow(QMainWindow):
    # class constructor

    def __init__(self):
        # call QWidget constructor
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        # self.setStyleSheet(open('stylesheet.css', 'r').read())

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

        # self.ui.rbtn1.clicked.connect(self.radio_clicked)
        # self.ui.rbtn2.clicked.connect(self.radio_clicked)
        # self.ui.rbtn3.clicked.connect(self.radio_clicked)
        # self.ui.imgLabel_1.mousePressEvent = self.instance_clicked

    def startInference(self):
        self.dataset = LoadImages(
            self.inputVideo, self.offset, img_size=640, stride=32)
        self.total_frame = self.dataset.nframes - self.offset
        self.th.total_frame = self.total_frame
        self.ui.slider.setMaximum(self.total_frame)
        self.inference = InferenceThread(self)
        self.inference.inference_signal.connect(self.updateInferenceStatus)
        self.inference.frame_info_signal.connect(self.addFrameInfo)
        self.inference.classes_signal.connect(self.updateCls)
        self.inference_status = INITIALIZED
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
                eval(f"self.ui.imgLabel_{i}.setText('EMPTY')")
        if self.magni < len(images):
            eval(
                f"self.ui.imgLabel_6.setPixmap(QPixmap.fromImage(images[{self.magni}]))")

    def offset_input(self):

        if self.ui.offset_input.toPlainText().isdigit():
            self.offset = int(self.ui.offset_input.toPlainText())
            print(self.offset)

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

    def RecordClicked(self):
        if self.inference_status == INFERENCE_FINISHED:
            self.incoding_th = IncodingThread(self.out_dir)
            self.incoding_th.start()
            self.incoding_th.record_signal.connect(self.updateInferenceStatus)
            self.incoding_th.record_progress.connect(self.recordStatusUpdate)

    @ pyqtSlot(str)
    def recordStatusUpdate(self, progress_text):
        incoded_frames = int(progress_text[6:12])
        s = f'{incoded_frames/2639:.2%} / '
        self.ui.record_status_label.setText(s + progress_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # create and show mainWindow
    mainWindow = MainWindow()
    mainWindow.show()

    sys.exit(app.exec_())

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


# def change_color(self, color):
#     template_css = """QProgressBar::chunk { background: %s; }"""
#     css = template_css % color
#     self.setStyleSheet(css)
