import glob
import os
import json
from os import walk
import re
import random
from subprocess import call

src_path = "/home/oem/data/catdog"
dst_path = "/home/oem/data/5frames"

for adir in os.listdir(src_path):    
    if adir.startswith('202'):
        for afile in os.listdir(os.path.join(src_path, adir)):
            if afile.endswith('mp4'):
                src = os.path.join(src_path,adir, afile)
                # print(src)
                clss = afile.split('-')[1]
                # print(clss)                
                dest = os.path.join(dst_path, clss, afile[:-4])                
                # if not os.path.exists(dest):     
                #     os.mkdir(dest)                                                    
                if len(glob.glob(dest + "/*.jpg")) < 64:                                            
                    dest = os.path.join(dest, 'img_%05d.jpg')  
                    print("extracting {} to {}".format(src, dest))              
                    # call(["ffmpeg", "-i", src, "-r", "5", "-threads", "32", dest])
                    call(["ffmpeg", "-i", src, "-r", "5", "-thread_type", "slice", dest])