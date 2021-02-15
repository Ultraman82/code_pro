import os
import shutil
import subprocess

root_dir = 'D:NIA_data\save_data\도심지'

def frame_extraction(src, dst):                
    print('sizeof_dst:', os.path.getsize(dst))
    #checking the destination folder is bigger than 1m
    if os.path.getsize(dst) < 1000000:        
        dst_shape = dst + '/%08d.jpg'
        print('starting extraction :', dst)
        subprocess.call(['ffmpeg', '-i', src, '-threads', '5', '-f',  'image2', dst_shape], shell=True)
        # extract_image = "ffmpeg -i {} -threads 5 -f image2 {}".format(src, dst)
        # subprocess.call(extract_image+'/%08d.jpg', shell=True)         
        print('making zip for :',dst)
        shutil.make_archive(dst, 'zip', dst)

for (root, dirs, files) in os.walk(root_dir):
    for afile in files:        
        if afile.endswith('MOV') or afile.endswith('MP4'):
            core_name = afile[:-4]
            dst_dir = os.path.join(root, core_name + '_image')
            if not os.path.isdir(dst_dir):
                os.makedirs(dst_dir)
            src_file = os.path.join(root, afile)
            frame_extraction(src_file, dst_dir)   