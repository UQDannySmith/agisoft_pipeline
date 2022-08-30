#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import pandas as pd
import matplotlib.pyplot as plt
import time
from tkinter import Tk, filedialog

import Metashape
#Metashape.License().activateOffline('C:\Program Files\Agisoft\Metashape Pro\metashape.lic')

import pipeline_functions_ as pf


# In[2]:


""" Set the working directory for a particular flight: This directory name should be the flight date yyyy-mm-dd and contain an OriginalImages folder
containing subfolders for each sensor, along with the flight height. i.e Altum_20m

"""
flight_dir = pf.dir_selector()

os.chdir(flight_dir)

try:
    if os.path.isdir("OriginalImages") == True:
        os.chdir("OriginalImages")
        print("you have selected {} as the flight directory\n".format(flight_dir))
    else:
        print("your flight directory needs to contain a folder named OriginalImages with subfolders for each sensor, along with the flight height. i.e Altum_20m")
except(WinError):
    print('no folder selected')


# In[3]:


""" 
This bit searches through the photos in the OriginalImages folder for their very first image.
With these images we can ensure the camera is multispec or RGB and name our chunks in Metashape accordingly...
"""


# Dictionary containing each sensor we use in lab: add to if necessary
sensors_we_use = {'FC6310S': 'RGB', 
                  'FC6360' : 'MS',
                  'ZenmuseP1': 'RGB',
                  'Altum': 'MS'
                 }

# Identify the folders containing flights
sensors = next(os.walk('.'))[1]

# READ EXIF TAGS OF FIRST IMAGE IN first_photo_list to obtain sensor info
first_photo_list = []
for i in range(len(sensors)):
    try:
        for topdir, dirs, files in os.walk(sensors[i], topdown=False, onerror=None, followlinks=False):
            firstfile = sorted(files, reverse=True)[0]
            first = os.path.join(topdir, firstfile)
            first_photo_list.append(first)
            break
    except:
        print("Error...")
        
from exiftool import ExifToolHelper
chunk_dict = {}

with ExifToolHelper() as et:
    for i in range(0,len(sensors)):
        d = et.get_metadata(first_photo_list[i])
        cam_params = {}
        cam_params['containing_folder'] = sensors[i]
        cam_params['Model'] = d[0]['EXIF:Model']
        cam_params['Make'] = d[0]['EXIF:Make']
        cam_params['SerialNumber'] = d[0]['EXIF:SerialNumber']
        cam_params['Date'] = d[0]['EXIF:CreateDate']
        cam_params['SensorType'] = sensors_we_use[d[0]['EXIF:Model']]
        cam_params['FirstPhoto'] = first_photo_list[i]
        chunk_dict[d[0]['EXIF:Model']] = cam_params


# In[4]:



# Get list of camera paths for all folders 
for chunk in chunk_dict:
ListOfFiles = list()
for (dirpath, dirnames, filenames) in os.walk(chunk_dict[chunk]['containing_folder']):
    ListOfFiles += [os.path.join(dirpath, file) for file in filenames]
    
num_photos = len(ListOfFiles)    
print('folder {} has {} photos'.format(chunk_dict[chunk]['containing_folder'], num_photos))
chunk_dict[chunk]['Number_of_photos'] = num_photos
chunk_dict[chunk]['camera_paths'] = ListOfFiles

print('Found all photos\n')


# In[5]:


###########################
# Create config file here #
###########################
# Info for exports (Don't put Underscores in these since XTRACTOR Won't like that)
group = 'UQ'
field_location = 'GilbertN'
trial = 'danNVT'
flight_date = pf.flight_date_getter(chunk_dict)
flight_height = '20m'

with open('../flight_log.txt', 'w') as f:
    f.write('Group: {}\nField location: {}\nFrial: {}\nFlight_date: {}\nFlight height: {}\n'.format(group, field_location, trial, flight_date, flight_height))
    
    f.write('\nLog File Info:\n')
    
    # Gets the log file from excel spreadsheet on Onedrive (Automatically updated from Microsoft Forms via power automate)
    log = pf.log_file_getter(flight_date)
    
    # If no log file for flight date available, do nothing
    if type(log) == str:
        f.write("{}\n".format(log))
        
    # Otherwise, put the following details in
    else:
        f.write('Operator ARN: {}\n'.format(log[0]))
        f.write('UAV: {}\n'.format(log[1]))
        f.write('Lighting conditions: {}\n'.format(log[2]))
        f.write('Wind conditions: {} m/s\n'.format(log[3]))    
    
    # Prints out sensor specific data
    i = 1
    for folder in chunk_dict:
        
        f.write('\n**********************\n')
        f.write('       Chunk {}       \n'.format(i))     
        f.write('**********************\n')
        f.write('Folder name: {}\n'.format(chunk_dict[folder]['containing_folder']))
        f.write('Sensor: {}\n'.format(chunk_dict[folder]['Model']))
        f.write('Make: {}\n'.format(chunk_dict[folder]['Make']))
        f.write('Serial Number: {}\n'.format(chunk_dict[folder]['SerialNumber']))
        f.write('Creation Date: {}\n'.format(chunk_dict[folder]['Date']))
        f.write('Sensor Type: {}\n'.format(chunk_dict[folder]['SensorType']))
        f.write('Number of Photos: {}\n'.format(chunk_dict[folder]['Number_of_photos']))
        
        # These may be useful for integration with Xtractor
        ortho_path = [group, field_location, trial, flight_date, '10-00-00', chunk_dict[folder]['Model'], pf.band_getter(chunk_dict,folder), flight_height, 'transparent', 'reflectance','packed.tif']
        ortho_path = "_".join(ortho_path)
        f.write('Ortho_filename: {}\n'.format(ortho_path))
        # add to dictionary just in case
        chunk_dict[folder]['ortho_path'] = ortho_path

        dem_path = [group, field_location, trial, flight_date, '10-00-00', chunk_dict[folder]['Model'], 'dsm.tif']
        dem_path = "_".join(dem_path)
        f.write('DEM_filename: {}\n'.format(dem_path))
        chunk_dict[folder]['dem_path'] = dem_path
        
        f.write('\n')
        i += 1
        
    f.close()
    
# export chunk dict as json for next files...
pf.export_dict(chunk_dict)
print('Created log file and exported cam parameters json\n')


# In[6]:


# Create new Metashape Document for this date
doc = Metashape.Document()
doc.save(path = "{}\{}.psx".format(flight_dir, str(flight_dir.split("/")[-1]))) #new empty project is created


# In[7]:


# Create Chunks for each sensor
i = 0
for name in chunk_dict:
    doc.addChunk()
    # Name the chunk by the sensor
    doc.chunks[i].label = name
    i+=1

doc.save()
for chunk in doc.chunks:
    print('created '+ chunk.label)

print("Created new chunks successfully\n")


# In[8]:


# Add photos to each chunk from camera_paths list...
for i in range(0,len(chunk_dict)):
    print('importing photos for {}'.format(doc.chunks[i].label))
    doc.chunks[i].addPhotos(chunk_dict[doc.chunks[i].label]['camera_paths']) # Adds all photos from each sensor to corresponding chunk
        
    doc.chunks[i].loadReferenceExif(load_accuracy = True,
                                    load_rotation = True)
    
doc.save()

# Import camera exif data
print('Cameras successfuly imported')


# In[9]:


# Convert EPSG to desired output
for chunk in doc.chunks:

    out_crs = Metashape.CoordinateSystem("EPSG::28356") #user-defined crs
    for camera in chunk.cameras:
        if camera.reference.location:
            camera.reference.location = Metashape.CoordinateSystem.transform(camera.reference.location, chunk.crs, out_crs)
    for marker in chunk.markers:
        if marker.reference.location:
            marker.reference.location = Metashape.CoordinateSystem.transform(marker.reference.location, chunk.crs, out_crs)
    chunk.crs = out_crs
    chunk.updateTransform()
    
    print('EPSG for {} updated to {}'.format(chunk, out_crs))

doc.save()
print('Updated EPSGs successfuly\n')


# In[10]:


# Estimate Image quality & Remove poor quality images

"""
values below 0.6 should be removed
"""
threshold = 0.6


for chunk in doc.chunks:
    
    print('estimating image quality for', chunk.label,'\n', end='\r')
    doc.chunk.analyzePhotos(progress = pf.progress_bar_print)
    count = 0    
    for j in range(0, len(doc.chunk.cameras)):
        camera = doc.chunk.cameras[j]
        quality = camera.frames[0].meta["Image/Quality"]
        
        # Altum thermal gives a quality value of zero, that's why zero is ignored below..
        if float(quality) < threshold and float(quality) != 0:
            camera.enabled = False
            #print("camera: {}, quality: {}, DISABLED".format(camera,quality))
            count += 1
    
    if count == 0:
        print('No images removed, all photos higher than threshold of {}'.format(threshold))
    else:
        print("{} photos removed from {} as quality lower than threshold {}".format(count, chunk.label, threshold))
    
    doc.save()
    
print('Quality check complete\n')


# In[11]:


# Radiometric Calibration
for i in range(0,len(chunk_dict)):
    #print(doc.chunks[i].label, sensors_we_use[doc.chunks[i].label])
    if sensors_we_use[doc.chunks[i].label] == 'MS':
        print('Performing Radiometric Calibration for {}'.format(doc.chunks[i].label))
        time.sleep(.5)
        
        # Normalize sensors
        print('Normalizing Sensors')
        for sensor in doc.chunks[i].sensors: #applying to all the sensors in the chunk
            sensor.normalize_sensitivity=True
        
        # Find QR Codes
        print('QR Code Matching')
        doc.chunks[i].locateReflectancePanels(progress=pf.progress_bar_print) # Locates Panel based on QR Code
        
        # Calibrate Reflectance
        print('Calibrating Reflectance Factors')
        doc.chunks[i].calibrateReflectance(use_reflectance_panels=True, use_sun_sensor=False, progress=pf.progress_bar_print)
    else:
        print("{} is RGB, radiometric calibration not needed".format(doc.chunks[i].label))
        time.sleep(.5)
        print('...')
doc.save()
print('Radiometric calibration complete\n')


# In[12]:


print("\nfinished setting up dataset. Next step is to open agisoft file and filter out unnecessary photos manually (i.e those taken between takeoff and the start point).This will considerably improve the alignment process")
get_ipython().run_line_magic('reset', '')

