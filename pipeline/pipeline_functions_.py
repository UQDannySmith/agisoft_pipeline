# Libraries
import os
import pandas as pd
import matplotlib.pyplot as plt
import time
from tkinter import Tk, filedialog
import Metashape

#!/usr/bin/env python
# coding: utf-8

# In[ ]:

# Functions for pipeline

# Metashape progress bar
def progress_print(p):
        print('Current task progress: {:.2f}%'.format(p),end="\r")

# Export Dictionary as Json
def export_dict(dictionary):   
    import json
    with open("../sensor_info.json", "w") as outfile:
        json.dump(dictionary, outfile)
        outfile.close()

# Read Dictionary from JSON
def import_dict():
    import json
    try:
        with open('sensor_info.json') as json_file:
            out = json.load(json_file)
            return(out)
    except FileNotFoundError:
        print('no json file found')

# defines band order
def band_getter(dictionary, folder):
    # This needs more sophistication! Altum band order is same as P4M but only since its a newer model
    # b = blue, g = green, r = red, e = red edge, n = nir, t = thermal
    if dictionary[folder]['SensorType'] == 'MS':
        return('bgren')
    else:
        return('rgb')
    
# Downloads log file from excel
def log_file_getter(flight_date):
    from datetime import datetime as dt
    df = pd.read_excel('C:\\Users\\uqdsmi34\\OneDrive - The University of Queensland\\uni_UQ_PhD\\equipment\\Gatton UAV log.xlsx')
    df['Date'] = pd.to_datetime(df['Start time']).dt.date
    df['Date'] = pd.to_datetime(df['Date'])
    filtered = df.loc[df['Date'] == flight_date ]
    if len(filtered) == 0:
        return('No log file matches the flight date')
    else:
        Op_ARN = filtered.iloc[0]['Enter your ARN']
        UAV = filtered.iloc[0]['Which UAV are you using']
        lighting = filtered.iloc[0]['Lighting Conditions']
        Wind = filtered.iloc[0]['Wind Speed']
        flight_params= [Op_ARN, UAV, lighting, Wind]
        return(flight_params)

# Gets the flight date
def flight_date_getter(dictionary):
    from datetime import datetime as dt
    f_date = []
    for chunk in dictionary:
        chunk_date = dt.strptime(dictionary[chunk]['Date'], "%Y:%m:%d %H:%M:%S").date()        
        f_date.append(chunk_date)

    if len(set(f_date)) > 1:
        #print(set(f_date))
        return(max(f_date).strftime(format="%Y-%m-%d"))

    else:
        #print(set(f_date))
        return(chunk_date.strftime(format="%Y-%m-%d"))
    

        
# Function to point to a directory 
def dir_selector():
    try:
        root = Tk() # pointing root to Tk() to use it as Tk() in program.
        root.withdraw() # Hides small tkinter window.
        root.attributes('-topmost',True)# Opened windows will be active. above all windows despite of selection.
        output = filedialog.askdirectory()# Returns opened path as str
        return(output)
    except(WinError):
        print('no folder selected')

# Selects a file        
def file_selector():
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost',True)
        output = filedialog.askopenfile()
        return(output)
    except(WinError):
        print('no file selected')

# GCP selector : Only works with default propeller aeropoint csv file
def aeropoint_selector():
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost',True)
        output = filedialog.askopenfilename(filetype=[("CSV Files", "*.csv")])
        gcps = open(output)
        lines = gcps.readlines()
        epsg = int(lines[9].split(',')[1])
        coord_sys = lines[8].split(',')[1]
        
        gcp_data = []
        
        for i in range(20,len(lines)):
            a = []
            a.append(lines[i].split(','))
            gcp_data.append(a)
        
        return(epsg,coord_sys, output)

    except(NameError):
        print('No file selected or check that the extension is a {}'.format(filetype))


def shp_get():
    import shutil
    import os
    from time import sleep
    shp_path = '..\\shp.zip'
    unzip_path = '..\\shp'
        
    # check if shape file already exists..
    if os.path.exists(shp_path):
        
        # select the shapefile
        for topdir, dirs, files in os.walk(unzip_path):
            file = [ fi for fi in files if fi.endswith(".shp") ][0]
            filepath = unzip_path + '\\' + file
            filepath = filepath.split('..')[-1]
            
        print("Shapefile found")
        return(filepath)
    
    else:
        shp = file_selector()
        print(shp.name)
        
        # make sure it's a zip file
        if shp.name.split('.')[-1] != 'zip':
            print('Needs to be zip')

        # Copy file
        else:
            shutil.copyfile(shp.name, shp_path)
            print('Successfully copied {}'.format(shp.name))
            import zipfile
            with zipfile.ZipFile(shp_path, 'r') as zip_ref:
                zip_ref.extractall(unzip_path)
            return(filepath)