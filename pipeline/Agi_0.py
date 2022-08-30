#!/usr/bin/env python
# coding: utf-8

# In[170]:


# This script can be used to copy images from SD Card or USB directly to the flight processing folder. 
import os
import pipeline_functions_ as pf

# Select folder containing UAV images:
print('Select the top folder either from the USB (Altum) or SD Card (other)')
StorageDevicePath = pf.dir_selector()

print('Select the parent directory where images will be stored')
DestinationPath = pf.dir_selector()

# Select image formats
formats = ['.tif','.tiff','.jpg','.jpeg']

import os
def original_date_get(filepath, filetype):
    
    from exiftool import ExifToolHelper
    from datetime import datetime, timedelta

    try:
        for topdir, dirs, files in os.walk(filepath, topdown=False, onerror=None, followlinks=False):
            for i in range(0,len(files)):
                #print(files)
                firstfile = sorted(files, reverse=True)[i]
                if '.'+ firstfile.split('.')[-1].lower() in formats:            
                    img = os.path.join(topdir, firstfile)
    except:
        print('error')
    
    # Return date of first image found
    with ExifToolHelper() as et:
        d = et.get_metadata(img)
        #print(d)
        
        # Altum is in UTC time for some reason and needs to be adjusted based on the timezone.
        if d[0]['EXIF:Model'] == 'Altum':
            print('Camera is Altum, adjusting for UTC time')
            import pytz
            from tzwhere import tzwhere

            tzwhere = tzwhere.tzwhere()
            timezone_str = tzwhere.tzNameAt(d[0]['Composite:GPSLatitude'], d[0]['Composite:GPSLongitude']) #Gets timezone from lat long
            timezone = pytz.timezone(timezone_str)
            dt = datetime.strptime(d[0]['EXIF:CreateDate'],'%Y:%m:%d %H:%M:%S')
            dates = str((dt + timezone.utcoffset(dt)).date())
            sensor = d[0]['EXIF:Model']
            return(dates, sensor)
        
        # The other sensors we use don't have this problem and EXIF:CreateDate is correct for the timezone
        else:
            print('Camera is {}, timezone is correct'.format(d[0]['EXIF:Model']))
            dt = datetime.strptime(d[0]['EXIF:CreateDate'],'%Y:%m:%d %H:%M:%S')
            dates = str(dt.date())
            sensor = d[0]['EXIF:Model']
            return(dates, sensor)

info = list_files(StorageDevicePath, formats)

# Copy contents to the output directory
from distutils.dir_util import copy_tree

date = info[0]
sensor = info[1]

flight_destination = DestinationPath  + '/' + date 
orig_imgs = flight_destination + '/OriginalImages'
sensor_destination = orig_imgs + '/' + sensor

if not os.path.isdir(flight_destination):
    os.mkdir(flight_destination)
    print('folder for flight date: {} created'.format(date))
    
if not os.path.isdir(orig_imgs):
    os.mkdir(orig_imgs)
    print('OriginalImages folder created')
    
if os.path.isdir(sensor_destination):
    choice = input('Sensor already exists here. Do you want to create another instance of this sensor for this date? Y/N')

    while choice != 'q':
        if choice.lower() == 'y':
            SensorsInDate = []
            for  topdir, dirs, files in os.walk(orig_imgs):
                SensorsInDate.append(dirs)  
            ind = 0
            for item in SensorsInDate[0]:
                if item.find(sensor) != -1:
                    ind += 1
            
            sensor_destination = sensor_destination + '_' + str(ind)
            os.mkdir(sensor_destination)
            
            print('Folder for {} created at path {}'.format(sensor, sensor_destination))
            copy_tree(StorageDevicePath, sensor_destination)
            
            break
            
        elif choice.lower() == 'n':
            print("Quitting")
            break
        
        else:
            print("That is not a valid input.")
        choice = input("What would you like to do (press q to quit)")
    
else:
    os.mkdir(sensor_destination)          
    print('folder for sensor: {} created at path {}'.format(sensor, sensor_destination))
    copy_tree(StorageDevicePath, sensor_destination)

