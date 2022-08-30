#!/usr/bin/env python
# coding: utf-8

# In[1]:


# Libraries
import os
import pandas as pd
import matplotlib.pyplot as plt
import time
from tkinter import Tk, filedialog
import Metashape

# Functions for pipeline
import pipeline_functions_ as pf


# In[2]:


# Select Metashape file, set working directory and open it
metashape_file = pf.file_selector().name

os.chdir("/".join(metashape_file.split('/')[0:-1]))

try:

    doc = Metashape.Document()
    doc.open(metashape_file.split('/')[-1])
 
    # Import chunk metadata dictionary
    chunk_dict = pf.import_dict()

    print('Metashape file imported successfully')
    
except:
    print('Error: Check to see that json file exists')


# In[3]:


# Enable GPU
Metashape.Application.gpu_mask = 0

# Perform Alignment for each chunk
"""
Reference preselection = source
Key point limit = [60,000].

Set Image quality:
Downscale - sets alignment accuracy: Highest = 0, High = 1, Medium = 2, Low = 4, Lowest = 8 (https://www.agisoft.com/forum/index.php?topic=11697.0)
Use reference_preselection for flights with GPS. Generic_preselection does a fast scan before the reference_preselection happens. Not 100% sure if it's necessary
"""

# Match settings
match = Metashape.Tasks.MatchPhotos()
match.generic_preselection = False
match.reference_preselection = True
match.reference_preselection_mode = Metashape.ReferencePreselectionSource
# Downscale refers to quality, For MatchPhotos:
# Highest = 0, High = 1, Medium = 2, Low = 4, Lowest = 8:
match.downscale = 1
match.tiepoint_limit = 60000

for i in range(0,len(chunk_dict)):
    print('matching photos for {}'.format(doc.chunks[i].label))
    match.apply(doc.chunks[i], progress = pf.progress_bar_print)
    doc.save()
    
print('All Chunks Matched')


# In[4]:


# Align Settings
align = Metashape.Tasks.AlignCameras()
align.adaptive_fitting = False
align.reset_alignment = True

for i in range(0,len(chunk_dict)):
    print('aligning photos for {}'.format(doc.chunks[i].label))
    align.apply(doc.chunks[i], progress = pf.progress_bar_print)
    print('\n')
    doc.save()
    
print('All Chunks aligned')


# In[5]:


# Change EPSG of all chunks to match that of GCPs
epsg = pf.aeropoint_selector()
print('The EPSG of your GCPs is: {}'.format(epsg))

out_crs = Metashape.CoordinateSystem("EPSG::{}".format(epsg[0])) #uses the epsg of the aeropoints

for i in range(0,len(chunk_dict)):
    for camera in doc.chunks[i].cameras:
        if camera.reference.location:
            camera.reference.location = Metashape.CoordinateSystem.transform(camera.reference.location, doc.chunks[i].crs, out_crs)
    for marker in doc.chunks[i].markers:
        if marker.reference.location:
            marker.reference.location = Metashape.CoordinateSystem.transform(marker.reference.location, chunk.crs, out_crs)
    doc.chunks[i].crs = out_crs
    doc.chunks[i].updateTransform()
    
print('All chunks are now in same CRS as GCPS')   


# In[ ]:


### NEED A BIT HERE THAT CHANGES MARKER ACCURACY FROM M TO MM (AEROPOINTS)...


# In[ ]:


# 2. Import GCPs
# Get GCPs
for i in range(0,len(chunk_dict)):
    doc.chunks[i].importReference(path = epsg[2], 
                                  format = Metashape.ReferenceFormatCSV, 
                                  columns='n|||||||yxzYXZ', 
                                  skip_rows=19, 
                                  crs = out_crs, 
                                  delimiter = ',', 
                                  create_markers=True)

doc.save()

print("\nfinished Aligning Chunks and importing GCPs. Next step is to open agisoft file and Manually place GCPs.\n")

# 3. stop for manual step (ADJUST MARKER HEIGHT AND THEN PLACE markers MANUALLY)
# Also create a shape and call it 'outerboundary.shp'


# In[ ]:


get_ipython().run_line_magic('reset', '')

