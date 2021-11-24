import argparse
from operator import index
import time
import json
from pathlib import Path
import os

import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path
from utils.plots import plot_one_box
from utils.torch_utils import select_device, load_classifier, time_synchronized

# added for threading
import threading
import queue


def frame_writer(q):
    while True:
        (save_frame, im0) = q.get()
        if save_frame == "over":
            break
        cv2.imwrite(save_frame, im0)


# def plot_one_box_local(x, img, color=None, label=None, line_thickness=3):
#     tl = line_thickness or round(
#         0.002 * (img.shape[0] + img.shape[1]) / 2) + 1  # line/font thickness
#     color = color or [random.randint(0, 255) for _ in range(3)]
#     c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
#     cv2.rectangle(img, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
#     if label:
#         tf = max(tl - 1, 1)  # font thickness
#         t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=3)[0]
#         c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
#         cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)  # filled
#         cv2.putText(img, label, (c1[0], c1[1] - 2), 0, tl / 3,
#                     [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)


def detect(model, dataset, output_dir):
    imgsz = 640
    webcam = False
    save_dir = output_dir
    if not os.path.exists(save_dir):  # output dir
        os.mkdir(save_dir)

    # Initialize
    # set_logging()
    device = select_device('')
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # Load model
    model = attempt_load(model, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size
    if half:
        model.half()  # to FP16

    # Set Dataloader
    vid_path, vid_writer = None, None

    # Get names and colors
    names = model.module.names if hasattr(model, 'module') else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in names]

    # Run inference
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(
            next(model.parameters())))  # run once
    t0 = time.time()
    for index, (path, img, im0s, vid_cap, cur_frame) in enumerate(dataset):
        instance_dir = os.path.join(save_dir, str(cur_frame))
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Inference
        t1 = time_synchronized()
        pred = model(img, augment=False)[0]

        # Apply NMS
        pred = non_max_suppression(
            pred, 0.30, 0.45, classes=False, agnostic=False)
        t2 = time_synchronized()

        q = queue.Queue(8)
        NWRITERS = 8
        threads = []
        for _ in range(NWRITERS):
            t = threading.Thread(target=frame_writer, args=(q,))
            t.start()
            threads.append(t)
        frame_info = {'count': {}}
        # Process detections
        bboxes = []
        for i, det in enumerate(pred):  # detections per image
            p, s, im0, frame = path, '', im0s, getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path
            s += '%gx%g ' % img.shape[2:]  # print string

            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(
                    img.shape[2:], det[:, :4], im0.shape).round()
                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    # add to string
                    class_name = names[int(c)]
                    s += f"{n} {class_name}{'s' * (n > 1)}, "

                # Write results
                for *xyxy, conf, cls in reversed(det):
                    label = f'{names[int(cls)]} {conf:.2f}'
                    # label = f'{names[int(cls)]} {index_instance}'

                    plot_one_box(xyxy, im0, label=label,
                                 color=colors[int(cls)], line_thickness=3)
                    # print(c1, c2)
                    x = int(xyxy[0])
                    y = int(xyxy[1])
                    w = int(xyxy[2] - xyxy[0])
                    h = int(xyxy[3] - xyxy[1])
                    bboxes.append([x, y, w, h])
            q.put((instance_dir + '.jpg', im0))
            # print(f'{s}Done. ({t2 - t1:.3f}s)')
        yield(index, bboxes)

    for _ in range(NWRITERS):
        q.put(("over", "over"))
    for thread in threads:
        thread.join()

    print(f'Done. ({time.time() - t0:.3f}s)')
