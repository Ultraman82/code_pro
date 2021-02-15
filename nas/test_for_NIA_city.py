import os
from datetime import datetime
import subprocess
import argparse
import pathlib
import re
import time
import zipfile
import csv
import time
import pysftp
import shutil
from urllib.parse import unquote
# file = pathlib.Path("guru99.txt")
# if file.exists ():
#     print ("File exist")
parser = argparse.ArgumentParser()
parser.add_argument('--save_data', default='D:/NIA_data/save_data',help='the dir to save video and json_folder')
parser.add_argument('--root_dir', default='D:/NIA_data',help='the dir to save video and json_folder')

args = parser.parse_args()

base_path = 'Z:\관광지'


print("Start Time : ", datetime.now())

host = '14.49.44.243'
port = 22
username = '08ulsan2'
password = '08ulsan2321'
hostkeys = None
cnopts = pysftp.CnOpts()

# Z:\관광지\대구_두류공원\4K 카메라\60m 이하\45도
location = '관광지'
areas = ['대구_화원유원지']
godos = ['60m 이하']
angles = ['90도']
print(location," 시작 ")

for area in sorted(areas):
	area_path = os.path.join(base_path, area, '4k 카메라')
	for godo in sorted(godos):
		godo_path = os.path.join(area_path, godo)
		
		# print(angle_folders)
		for angle_folder in angles:
			angle_folder_path = os.path.join(godo_path, angle_folder)
			an_folders = sorted(os.listdir(os.path.join(angle_folder_path)))
			# print(an_folders)
			for an_folder in sorted(an_folders):
				from_path = os.path.join(angle_folder_path, an_folder)
				# print(from_path)
				# to_path = os.path.join(args.save_data, location, an_folder)
				to_path = args.save_data + '/'+ location + '/' + an_folder
				# print("to_path: ", to_path)
				if not os.path.exists(os.path.join(args.save_data, location)):
					os.mkdir(os.path.join(args.save_data, location))
					print("Directory ", os.path.join(args.save_data, location), " Created")
				else:
					print("Directory ", os.path.join(args.save_data, location), "already exists")
				if not os.path.exists(to_path):
					os.mkdir(to_path)
					print("Directory ", to_path, " Created")
				else:
					print("Directory ", to_path, "already exists")
				print("NAS에서 이동하는 데이터 폴더 : ", from_path)
				print("로컬 머신 어디에 ? : ", to_path)
				#sending for json_data from nas to local path
				if os.path.exists(os.path.join(from_path, 'json_folder')):
					json_folders = sorted(os.listdir(os.path.join(from_path, 'json_folder')))
					video_folders = sorted(os.listdir(os.path.join(from_path, 'video')))
							
				
					for json_folder, video_folder in zip(json_folders, video_folders):
						hub_name = json_folder.split('.')[0]
						ftp_name = hub_name + '_image.zip'
						file_info = json_folder.split('_')
						explain_image = location + '/' + area +'/' + file_info[2] +'/' + file_info[5] + '/image' 
						explain_json = location + '/' + area +'/' + file_info[2] +'/' + file_info[5] + '/json' 
						with open(os.path.join(args.root_dir,'write.csv'), 'a', newline='') as f:
							wr = csv.writer(f)
							wr.writerow([ftp_name,hub_name+'_image',explain_image])
							wr.writerow([json_folder,hub_name+'_json',explain_json])
						# print(json_folder)
						# json_folder_path = os.path.join(from_path, 'json_folder', json_folder)
						json_folder_path = from_path + '/json_folder' + '/' + json_folder
						# video_folder_path = os.path.join(from_path,'video',video_folder)
						video_folder_path = from_path + '/video' + '/' + video_folder
						# print(json_folder_path)
						# print('to_path',to_path)
						start_json_download = time.time()

						shutil.copy(json_folder_path, to_path)

						Take_time_for_json = time.time() - start_json_download
						print("Time for json download: ", Take_time_for_json)
						
						
						video_name = video_folder_path.split('/')[-1]
						video_date_name = video_name.split('.')[0]
						video_exist = to_path + '/' + video_name
						
						
						if not os.path.exists(video_exist):
							print("video download start ", video_exist)
							try:
								if not os.path.exists('{}.zip'.format(os.path.join(to_path, video_name.split('.')[0]+'_image'))):
									start_video_download = time.time()
									# os.system('rsync -avz \'{}\' \'{}\''.format(video_folder_path, to_path))
									shutil.copy(video_folder_path, to_path)
									Take_time_for_video = time.time() - start_video_download
									print("1. Complete Video Download ", video_name, "Time for video download: ", Take_time_for_video)
									time.sleep(3)
							except:
								with open(os.path.join(args.root_dir, 'fail_video_download_{}_{}.csv'.format(location, godo)), 'a', newline='') as fv:
									wr_v1 = csv.writer(fv)
									wr_v1.writerow([video_name])
							file_info = json_folder.split('_')
							explain_image = location + '/' + area +'/' + file_info[2] +'/' + file_info[5] + '/image' 
							explain_json = location + '/' + area +'/' + file_info[2] +'/' + file_info[5] + '/json' 
							with open(os.path.join(args.root_dir, 'write.csv'),'a', newline='') as f:
								wr = csv.writer(f)
								wr.writerow([ftp_name,hub_name+'_image',explain_image])
								wr.writerow([json_folder,hub_name+'_json',explain_json])
							try:
								print("extract video -> image")
								if not os.path.exists(to_path + '/' + video_name.split('.')[0]+'_image'):
									os.mkdir(to_path + '/' + video_name.split('.')[0]+'_image')
								start_extract_image = time.time()
								extract_image = "ffmpeg -i {} -f image2 {}".format(video_exist, to_path + '/' + video_name.split('.')[0]+'_image')
								# subprocess.call(extract_image+'/%08d.jpg', shell=True)
								os.system(extract_image+'/%08d.jpg')
								Take_time_for_extract_image = time.time() - start_extract_image
								print("Time for extract_image: ", Take_time_for_extract_image)
							except:
								with open(os.path.join(args.root_dir, 'fail_extract_video.csv_{}_{}.csv'.format(location, godo)), 'a', newline='') as fev:
									wr_v1 = csv.writer(fev)
									wr_v1.writerow([video_name])

						elif os.path.exists(video_exist):
							# if not os.path.exists(os.path.join(to_path, video_name.split('.')[0]+'_image')):
							try:
								if not os.path.exists(os.path.join(to_path, video_name.split('.')[0]+'_image')):
									os.mkdir(os.path.join(os.path.join(to_path, video_name.split('.')[0]+'_image')))
								start_extract_image = time.time()
								extract_image = "ffmpeg -i {} -f image2 {}".format(video_exist, to_path + '/' + video_name.split('.')[0]+'_image')
								# extract_image = "ffmpeg -i {} -f image2 -r 1 {}".format(video_exist, to_path + '/' + video_name.split('.')[0]+'_image')#1frame으로 출력하고 싶으면 -r 1 적용
								os.system(extract_image+'/%08d.jpg')
								Take_time_for_extract_image = time.time() - start_extract_image
								print("Time for extract_image: ", Take_time_for_extract_image)
								with open(os.path.join(args.root_dir, 'complete_extract_video_{}_{}.csv'.format(location, godo)),'a', newline='') as file:
									wr_v = csv.writer(file)
									wr_v.writerow([video_name])
							except:
								with open(os.path.join(args.root_dir, 'fail_video_download.csv_{}_{}.csv'.format(location, godo)),'a', newline='') as fev2:
									wr_v = csv.writer(fev2)
									wr_v.writerow([video_name])
						if not os.path.exists('{}.zip'.format(os.path.join(to_path, video_name.split('.')[0]+'_image'))):
							with zipfile.ZipFile('{}.zip'.format(os.path.join(to_path, video_name.split('.')[0]+'_image')),'w') as make_zip:	
								start_zip_image = time.time()
								for filename in sorted(os.listdir(os.path.join(to_path, video_name.split('.')[0]+'_image'))):
									make_zip.write(os.path.join(to_path, video_name.split('.')[0]+'_image', filename))
								Take_time_for_zip = time.time() - start_zip_image
								print("Time for zip_image: ", Take_time_for_zip)
'''
#############################################################################################################################################################################
### 업로드하기 위해서는 아래 코드 사용 필요
						# sftp 접속을 실행
						if cnopts.hostkeys.lookup(host) == None:
							print("Hostkey for " + host + " dosen't exist")
							hostkeys = cnopts.hostkeys
							cnopts.hostkeys = None
						with pysftp.Connection(
												host,
												port = port,
												username = username,
												password = password,
												cnopts = cnopts) as sftp:
							
							# 접속이 완료된 후 이 부분이 호스트키를 저장하는 부분
							# 처음 접속 할 때만 실행되는 코드
							if hostkeys != None:
								print("New Host. Caching hostkey for " + host)
								hostkeys.add(host, sftp.remote_server_key.get_name(), sftp.remote_server_key) # 호스트와 호스트키를 추가
								hostkeys.save(pysftp.helpers.known_hosts()) # 새로운 호스트 정보 저장
							

							if not sftp.exists('/files/01.데이터/2.Validation/라벨링데이터' + '/' + location + '/' + video_date_name):
								sftp.mkdir('/files/01.데이터/2.Validation/라벨링데이터/' + location + '/' + video_date_name, mode=777)
								# print("exists?????????", sftp.exists('/files/01.데이터/2.Validation/라벨링데이터' + '/' + location + '/' + video_date_name))
								time.sleep(2)
							else:
								continue

							print("to_path",to_path)
							local_data_path_zip = to_path + '/' + json_folder

							print("start upload json zip")
							start_upload_zip_image = time.time()
							print("local local_data_path_zip: ", local_data_path_zip)
							# print("sftp path: ", sftp_data_path)

							print("start upload image zip")
							local_data_path_zip = os.path.join(to_path, video_name.split('.')[0] + '_image.zip')
							start_upload_image = time.time()
							print("local path: ", os.path.join(to_path, video_name.split('.')[0] + '_image.zip'))
							print("sftp path: ", os.path.join('/files/01.데이터/2.Validation/라벨링데이터', location, video_date_name, video_name.split('.')[0] + '_image.zip'))
							with sftp.cd('/files/01.데이터/2.Validation/라벨링데이터' + '/' + location + '/' + video_date_name):
								sftp.put(local_data_path_zip, preserve_mtime=True)
							print("finish upload image zip", "Time: ", time.time() - start_upload_image)
							time.sleep(2)
#############################################################################################################################################################################
# 							## remove json_zip
							
# 							try:
# 								os.remove(os.path.join(to_path, json_folder))
# 								os.remove(os.path.join(to_path, video_name.split('.')[0] + '_image.zip'))
# 								shutil.rmtree(os.path.join(to_path, video_name.split('.')[0] + '_image'))
# 								os.remove(os.path.join(to_path, video_name))
# 							except:
# 								pass
'''
