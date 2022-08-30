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


# In[14]:


# Optimise alignment
# 1. deselect cameras

for i in range(0,len(chunk_dict)):
    for j in range(0,len(doc.chunks[i].cameras)):
        camera = doc.chunks[i].cameras[j]
        camera.selected = False
        
    print("all cameras deselected from {} \n".format(doc.chunks[i]))
    doc.save()

# 2. Optimise cameras

for i in range(0,len(doc.chunks)):
    print('Optimising {}\n'.format(doc.chunks[i]))
    doc.chunks[i].optimizeCameras(adaptive_fitting=True, progress=pf.progress_bar_print)
    


# In[19]:


# Calculate GCP errors:
for i in range(0,len(chunk_dict)):
    listaErrores = []
    for marker in doc.chunks[i].markers:

       source = doc.chunks[i].crs.unproject(marker.reference.location) #measured values in geocentric coordinates

       estim = doc.chunks[i].transform.matrix.mulp(marker.position) #estimated coordinates in geocentric coordinates

       local = doc.chunks[i].crs.localframe(doc.chunks[i].transform.matrix.mulp(marker.position)) #local LSE coordinates

       error = local.mulv(estim - source)

       total = error.norm()      #error punto
       SumCuadrado = (total) ** 2    #cuadrado del error
       listaErrores += [SumCuadrado]      #lista de los errores
    #print(listaErrores)

    suma = sum(listaErrores)
    n = len(listaErrores)
    print("{} - Sum of Errors: {}, Number of Markers: {}".format(doc.chunks[i].label, suma, n))
    try:
        ErrorTotal = (suma / n) ** 0.5
        print("Total Marker Error: {}\n".format(round(ErrorTotal, 4)))
    except(ZeroDivisionError):
        print('No Markers in chunk: {}. Error not calculatable'.format(doc.chunks[i].label))

    # Maybe put a dialog here for when error value is above threshold, so that they can have option to abort and check marker quality manually...


# In[20]:


# Enable GPU
Metashape.Application.gpu_mask = 0

# Build Dense Cloud / Depth Maps
# Depth Maps
depth = Metashape.Tasks.BuildDepthMaps()
# Downscale refers to quality: For Depth Maps
# Ultra = 1, High = 2, Medium = 4, Low = 8, Lowest = 16:
# See memory Requirements for more info: http://www.agisoft.com/pdf/tips_and_tricks/PhotoScan_Memory_Requirements.pdf
depth.downscale = 2
depth.filter_mode = Metashape.MildFiltering

# Dense cloud
dense = Metashape.Tasks.BuildDenseCloud()
dense.keep_depth = False
dense.point_colors = True
dense.point_confidence = False

for i in range(0,len(chunk_dict)):
    print('Building Depth Maps for {}\n'.format(doc.chunks[i].label))
    depth.apply(doc.chunks[i], progress = pf.progress_bar_print)    
    doc.save()
    
for i in range(0,len(chunk_dict)):  
    print('Building Dense Cloud for {}\n'.format(doc.chunks[i].label))
    dense.apply(doc.chunks[i], progress = pf.progress_bar_print)   
    doc.save()


# In[26]:


# Build DEM
dem = Metashape.Tasks.BuildDem()
dem.source_data = Metashape.DenseCloudData
dem.interpolation = Metashape.EnabledInterpolation
dem.projection = doc.chunks[0].crs

for i in range(0,len(chunk_dict)):
    print('Building DEM for {}\n'.format(doc.chunks[i].label))
    dem.apply(doc.chunks[i], progress = pf.progress_bar_print)    
    doc.save()


# In[28]:


#Build Orthomosaic
ortho = Metashape.Tasks.BuildOrthomosaic()
ortho.surface_data = Metashape.ElevationData
ortho.blending_mode = Metashape.MosaicBlending
ortho.fill_holes = True
ortho.cull_faces = False
ortho.refine_seamlines = True
ortho.ghosting_filter = False
ortho.projection = doc.chunks[0].crs

for i in range(0,len(chunk_dict)):
    print('Building Orthomosaic for {}\n'.format(doc.chunks[i]))
    ortho.apply(doc.chunks[i], progress = pf.progress_bar_print)    
    doc.save()


# In[35]:


for chunk in chunk_dict:
    print("output/ortho/"+chunk_dict[chunk]['ortho_path'])


# In[4]:


# Export Ortho

compress = Metashape.ImageCompression()
compress.tiff_big = True
compress.jpeg_quality = 90
project = Metashape.OrthoProjection()
project.crs = doc.chunks[0].crs
#compression.tiff_compression = compression.TiffCompressionLZW 


# In[4]:


# Separate RGB and MS ortho outputs
for i in range(0,len(chunk_dict)):
    if chunk_dict[doc.chunks[i].label]['SensorType'] == 'MS':
        print('Exporting Multispec: {}\n'.format(doc.chunks[i].label))
        doc.chunks[i].exportRaster(path = "output/ortho/MS/"+chunk_dict[doc.chunks[i].label]['ortho_path'],                                                                                                                            
                                  source_data = Metashape.OrthomosaicData,
                                  image_compression = compress,
                                  projection = project,
                                  clip_to_boundary = True)
        
    elif chunk_dict[doc.chunks[i].label]['SensorType'] == 'RGB':
        print('Exporting RGB: {}\n'.format(doc.chunks[i].label))
        doc.chunks[i].exportRaster(path = "output/ortho/RGB/"+chunk_dict[doc.chunks[i].label]['ortho_path'],                                                                                                                            
                                  source_data = Metashape.OrthomosaicData,
                                  image_compression = compress,
                                  projection = project,
                                  clip_to_boundary = True)
    
    doc.save()


# In[5]:


# Export DEM
"""
Path = output/DEMS/sensor_make_dem_date.tif
Format = TIFF/ GeoTIFF
Projection = Project CRS
No-Data value = -32767
Clip to Boundary Shapes = Yes
Write BigTiff = Yes
Tiff Compression = LZW
JPEG Quality = 90
Save Alpha = Yes
"""

# Separate RGB and MS ortho outputs
for i in range(0,len(chunk_dict)):
    if chunk_dict[doc.chunks[i].label]['SensorType'] == 'MS':
        print('Exporting DEM: {}\n'.format(doc.chunks[i].label))
        doc.chunks[i].exportRaster(path = "output/DEM/MS/"+chunk_dict[doc.chunks[i].label]['dem_path'],                                                                                                                            
                                  source_data = Metashape.ElevationData,
                                  image_compression = compress,
                                  projection = project,
                                  clip_to_boundary = True)
        
    elif chunk_dict[doc.chunks[i].label]['SensorType'] == 'RGB':
        print('Exporting DEM: {}\n'.format(doc.chunks[i].label))
        doc.chunks[i].exportRaster(path = "output/DEM/RGB/"+chunk_dict[doc.chunks[i].label]['dem_path'],                                                                                                                            
                                  source_data = Metashape.OrthomosaicData,
                                  image_compression = compress,
                                  projection = project,
                                  clip_to_boundary = True)
    
    doc.save()
 


# In[42]:


# Generate Report
for i in range(0,len(chunk_dict)):
    doc.chunks[i].exportReport(path='output/reports/'+doc.chunks[i].label+'.pdf', title=doc.chunks[i].label+' Report')

# Email Notify 

doc.save()
get_ipython().run_line_magic('reset', '')

