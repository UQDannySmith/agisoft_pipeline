#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
# Functions for pipeline
import pipeline_functions_ as pf
import time

# Select Metashape file, set working directory and open it
print('select agisoft file')
time.sleep(0.5)
metashape_file = pf.file_selector().name

os.chdir("/".join(metashape_file.split('/')[0:-1]))

# Import chunk metadata dictionary
chunk_dict = pf.import_dict()

# go through the chunk dictionary to assign the RGB and MS orthomosaics
ortho_dict = {}
for chunk in chunk_dict:
    if chunk_dict[chunk]['SensorType'] == 'MS':
        ortho_dict['MS'] = chunk_dict[chunk]['ortho_path']
    elif chunk_dict[chunk]['SensorType'] == 'RGB':
        ortho_dict['RGB'] = chunk_dict[chunk]['ortho_path']
        
shp_filename = pf.shp_get()


# In[7]:


# -*- coding: utf-8 -*-
"""
Xtractor V2 Beta Edition
"""
from PIL import Image, ImageOps , ImageDraw
from sys import argv, stdout, stderr, exit
import numpy as np
import tifffile
import matplotlib.pyplot as plt
import matplotlib.path as path
import shapefile
import glob
import os
#import numpy.random.common
#import numpy.random.bounded_integers
#import numpy.random.entropy
import laspy
import cv2
import math

#
#

MaskOtsu = True
scaling_factor= 32768
min_area = 0.01
min_distance = 5
PlantCountMaskLevel = 0.2
plantcountinidicechoice = 'osavi'
masklist = ['osavi','ndvi','ndre_r']
masklevels = 0.5
indecises_list = ['osavi','ndvi','ndre_r','dvi','gemi','msavi2','exg','clre','evi']
#for output colouring
#plotcolourrange = {'osavi':1,'ndvi':1,'ndre_r':1,'dvi':1,'gemi':1.5,'msavi2':1,'exg','clre':15,'evi'}
PlotColourMap = {'osavi':cv2.COLORMAP_JET,'ndvi':cv2.COLORMAP_SUMMER,'ndre_r':cv2.COLORMAP_HOT,'dvi':cv2.COLORMAP_WINTER,'gemi':cv2.COLORMAP_WINTER,'msavi2':cv2.COLORMAP_VIRIDIS,'exg':cv2.COLORMAP_PARULA,'clre':cv2.COLORMAP_COOL,'evi':cv2.COLORMAP_AUTUMN}
PercentileList = [i for i in range(1,100)]
PlotBuffer = 100
CalcHeights = True

def process_file(filename,shapefilename,outputfile,first_file, input_location,ground):
    imageIn = tifffile.imread(filename, key=0)
    FileLocation, TiffName = os.path.split(filename)
    thermal_attatched=False
    outputvars = TiffName.split('_')
    if len(outputvars)<=7:
        print('file not in correct format'+TiffName)
        return
    global date_v
    global time_v
    global trial_v
    global camera_v
    global height_v
    global indecises_list
    date_v = outputvars[3]
    time_v = outputvars[4]
    trial_v = ' '.join(outputvars[1:3])
    camera_v = outputvars[5]
    height_v = outputvars[7]
    
    band={}
    with tifffile.TiffFile(filename) as tif:
        scale = tif.pages[0].tags['ModelPixelScaleTag'].value
        TiePoint = tif.pages[0].tags['ModelTiepointTag'].value
    print(imageIn.shape)
    if(imageIn.shape[2]>5):  
        if 'temperature' not in indecises_list:
            indecises_list.append('temperature')
        thermal = imageIn[:,:,5]
        thermal_attatched = True
        thermal2 = thermal.astype(float)
            #Create Thermal Scale
        thermal2 = thermal2/100-273.15
        thermal2[thermal2==-273.15]=0.0
        band['thermal'] = thermal2
        del thermal
        del thermal2
    else:
        if 'temperature' in indecises_list:
            indecises_list.remove('temperature')        

        
    if(CalcHeights):
        for tif_file in glob.glob(dem_location+'\\*'+date_v+"*dsm.tif"):
            HimageIn = tifffile.imread(tif_file, key=0)
            #print(HimageIn.shape)
            band['heights']=HimageIn.astype(float)
            #print(tif_file)
            del HimageIn
        
            

    # the following indices were based on a 'red, green, blue, re, nir' set of descriptions, so these mappings
    # were used here: red=r_670, green=r_550, blue=r_400, re=r_710, nir=r_800
    if(np.nanmax(imageIn[:,:,0])<1):
        scaling_factor = 1   
    elif(np.nanmax(imageIn[:,:,0])<1000):
        scaling_factor = 327.68
    elif(np.nanmax(imageIn[:,:,0])<100):
        print('Input values low lost data depth')
        scaling_factor = 32.768
    elif(np.nanmax(imageIn[:,:,0])<10):
        scaling_factor = 3.2768
        print('Input values low lost data depth')

    else:
        scaling_factor = 32768
    print("Scaling factor used: " + str(scaling_factor))
    band['r_400'] = imageIn[:,:,0].astype(float)/scaling_factor
    band['r_550'] = imageIn[:,:,1].astype(float)/scaling_factor
    band['r_670'] = imageIn[:,:,2].astype(float)/scaling_factor
    band['r_710'] = imageIn[:,:,3].astype(float)/scaling_factor
    band['r_800'] = imageIn[:,:,4].astype(float)/scaling_factor
    #band['r_670'][band['r_670']==0]=1



    #Clean up some ram
    del imageIn

    #rotate and crop file to just plot area
    band,plots,textlocation,corners  = rotateAndCrop(band,shapefilename,TiePoint,scale) 
    
    # #Create And Calculate Coverage
    print('Making Masks:')
    masks = {}
    maskThreshold = {}
    for maskname in masklist:
        print(maskname)
        TempMask = indice_calculation(band,maskname)
        createimage(TempMask,plots,maskname,textlocation)
        creategridimage(TempMask,plots,maskname,textlocation)
        TempMask = (TempMask*(255)).astype(np.uint8)
        if(MaskOtsu == True):
            (T, masks[maskname]) = cv2.threshold(TempMask, 0, 1,cv2.THRESH_OTSU)
            maskThreshold[maskname] = T/255 
        else:
            (T, masks[maskname]) = cv2.threshold(TempMask, (masklevels*255), 1,cv2.THRESH_OTSU)
            maskThreshold[maskname] = T/255 
        masks[maskname] = masks[maskname].astype(np.uint8)
        CalculateCoverage(masks[maskname],plots,maskname,corners)
        #createimage(masks[maskname],plots,maskname+"_mask",textlocation)

    print('Calculating Indices:')
    
    CalculateIndices(band,masks,maskThreshold,plots,corners)
    if 'heights' in band.keys():
        CalculateHeights(band['heights'],masks,maskThreshold,plots,corners,ground,scale)
    else:
        print('No Height file for: ' + date_v)
        
def CalculateHeights(data,masks,maskThreshold,plots,corners,ground,scale):
    xyarea = scale[0]*scale[1]
    for plot in plots:
        plotData = np.array(data[(corners[plot][2]):(corners[plot][3]),(corners[plot][0]):(corners[plot][1])])
        #do full plot
        try:
            
            plotValues = plotData-ground[plot]

            writeDatatoFile(np.sum(plotValues*xyarea),plot,'height','volume','no mask','no threshold')
            writeDatatoFile(np.percentile(plotValues,2),plot,'height','x2nd Percentile','no mask','no threshold')
            writeDatatoFile(np.percentile(plotValues,25),plot,'height','x25th Percentile','no mask','no threshold')
            writeDatatoFile(np.percentile(plotValues,50),plot,'height','x50th Percentile','no mask','no threshold')
            writeDatatoFile(np.percentile(plotValues,75),plot,'height','x75th Percentile','no mask','no threshold')
            writeDatatoFile(np.percentile(plotValues,95),plot,'height','x95th Percentile','no mask','no threshold')    
            writeDatatoFile(np.percentile(plotValues,98),plot,'height','x98th Percentile','no mask','no threshold')
            writeDatatoFile(((plotValues[plotValues<=0.25]).size/plotValues.size),plot,'height','xAreaBelow25','no mask','no threshold')
            writeDatatoFile(((plotValues[plotValues<=0.50]).size/plotValues.size),plot,'height','xAreaBelow50','no mask','no threshold')
            writeDatatoFile(((plotValues[plotValues<=0.75]).size/plotValues.size),plot,'height','xAreaBelow75','no mask','no threshold')
            #if indice=='osavi':
                #createimagesingleplot(plotValues,plot)
        #do for each mask value
            for mask in masks:
                plotMask = masks[mask][(corners[plot][2]):(corners[plot][3]),(corners[plot][0]):(corners[plot][1])]
                maskedPlotValues = plotValues[plotMask>0]
                if(maskedPlotValues.size>0):
                    writeDatatoFile(np.sum(maskedPlotValues*xyarea),plot,'height','volume',mask,maskThreshold[mask])
                    writeDatatoFile(np.percentile(maskedPlotValues,2),plot,'height','x2nd Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(np.percentile(maskedPlotValues,25),plot,'height','x25th Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(np.percentile(maskedPlotValues,50),plot,'height','x50th Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(np.percentile(maskedPlotValues,75),plot,'height','x75th Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(np.percentile(maskedPlotValues,95),plot,'height','x95th Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(np.percentile(maskedPlotValues,98),plot,'height','x98th Percentile',mask,maskThreshold[mask])
                else:
                    writeDatatoFile(0,plot,'height','x2nd Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(0,plot,'height','x25th Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(0,plot,'height','x50th Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(0,plot,'height','x75th Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(0,plot,'height','x95th Percentile',mask,maskThreshold[mask])
                    writeDatatoFile(0,plot,'height','x98th Percentile',mask,maskThreshold[mask])                    
        except:
            print("failed plot")        
        
def plant_count(img,plots,plancountfile) :
    params = cv2.SimpleBlobDetector_Params()
    params.filterByCircularity = False;
    params.filterByConvexity = False;
    params.filterByInertia = False;
    params.filterByArea = True;
    params.minArea = min_area;
    params.minDistBetweenBlobs = min_distance;
    detector = cv2.SimpleBlobDetector_create(params)
    keypoints = detector.detect(img)
    im_with_keypoints = cv2.drawKeypoints(im, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    createimage(data,plots,plotname,textlocation)
    
    
    
def CalculateIndices(data,masks,maskThreshold,plots,corners):
    for plot in plots:
        plotData={}
        for band in data:
            plotData[band] = data[band][(corners[plot][2]):(corners[plot][3]),(corners[plot][0]):(corners[plot][1])]

        #do full plot
        for indice in indecises_list:
            try:
                plotValues = indice_calculation(plotData,indice)
                writeDatatoFile(np.nanmean(plotValues),plot,indice,'mean','no mask','no threshold')
                writeDatatoFile(np.nanmedian(plotValues),plot,indice,'median','no mask','no threshold')
                writeDatatoFile(np.nanmin(plotValues),plot,indice,'min','no mask','no threshold')
                writeDatatoFile(np.nanmax(plotValues),plot,indice,'max','no mask','no threshold')
                writeDatatoFile(np.nanstd(plotValues),plot,indice,'StdDev','no mask','no threshold')
                if indice == 'temperature':
                    m2_q = np.nanquantile(plotValues,[0.05,0.25])
                    filter_arr=[]
                    for row in plotValues:
                        for element in row:
                            if element > m2_q[0] and element <= m2_q[1]:
                                filter_arr.append(element)
                    m2 = np.mean(filter_arr)
                    writeDatatoFile(m2,plot,indice,'m2','no mask','no threshold')
                #if indice=='osavi':
                    #createimagesingleplot(plotValues,plot)
            #do for each mask value
                for mask in masks:
                    plotMask = masks[mask][(corners[plot][2]):(corners[plot][3]),(corners[plot][0]):(corners[plot][1])]
                    maskedPlotValues = plotValues[plotMask>0]
                    if(maskedPlotValues.size>0):
                        writeDatatoFile(np.nanmean(maskedPlotValues),plot,indice,'mean',mask,maskThreshold[mask])
                        writeDatatoFile(np.nanmedian(maskedPlotValues),plot,indice,'median',mask,maskThreshold[mask])
                        writeDatatoFile(np.nanmin(maskedPlotValues),plot,indice,'min',mask,maskThreshold[mask])
                        writeDatatoFile(np.nanmax(maskedPlotValues),plot,indice,'max',mask,maskThreshold[mask])
                        writeDatatoFile(np.nanstd(maskedPlotValues),plot,indice,'StdDev',mask,maskThreshold[mask])
                    else:
                        writeDatatoFile(0,plot,indice,'mean',mask,maskThreshold[mask])
                        writeDatatoFile(0,plot,indice,'median',mask,maskThreshold[mask])
                        writeDatatoFile(0,plot,indice,'min',mask,maskThreshold[mask])
                        writeDatatoFile(0,plot,indice,'max',mask,maskThreshold[mask])
                        writeDatatoFile(0,plot,indice,'StdDev',mask,maskThreshold[mask])                    
            except:
                print("failed plot")


def processemergencedata(first_file,shapefilename,input_location):
    file_location = input_location+'\\'+first_file
    
    imageIn = tifffile.imread(file_location, key=0)
    #FileLocation, TiffName = os.path.split(first_file)
    thermal_attatched=False
    outputvars = first_file.split('_')
    if len(outputvars)<=7:
        print('file not in correct format'+TiffName)
        return
    global date_v
    global time_v
    global trial_v
    global camera_v
    global height_v    
    date_v = outputvars[3]
    time_v = outputvars[4]
    trial_v = ' '.join(outputvars[1:3])
    camera_v = outputvars[5]
    height_v = outputvars[7]
    
    band={}
    with tifffile.TiffFile(file_location) as tif:
        scale = tif.pages[0].tags['ModelPixelScaleTag'].value
        TiePoint = tif.pages[0].tags['ModelTiepointTag'].value
    print(imageIn.shape)
    if(imageIn.shape[2]>5):    
        thermal = imageIn[:,:,5]
        thermal_attatched = True
        thermal2 = thermal.astype(float)
            #Create Thermal Scale
        thermal2 = thermal2/100-273.15
        thermal2[thermal2==-273.15]=0.0
        band['thermal'] = thermal2
        del thermal
        del thermal2
        
    if(CalcHeights):
        for tif_file in glob.glob(dem_location+'\\*'+date_v+"*dsm.tif"):
            HimageIn = tifffile.imread(tif_file, key=0)
            print(HimageIn.shape)
            band['heights']=HimageIn.astype(float)
            print(tif_file)
            del HimageIn
        
            

    # the following indices were based on a 'red, green, blue, re, nir' set of descriptions, so these mappings
    # were used here: red=r_670, green=r_550, blue=r_400, re=r_710, nir=r_800
    if(np.nanmax(imageIn[:,:,0])<1):
        scaling_factor = 1   
    elif(np.nanmax(imageIn[:,:,0])<1000):
        scaling_factor = 327.68
    elif(np.nanmax(imageIn[:,:,0])<100):
        print('Input values low lost data depth')
        scaling_factor = 32.768
    elif(np.nanmax(imageIn[:,:,0])<10):
        scaling_factor = 3.2768
        print('Input values low lost data depth')

    else:
        scaling_factor = 32768
    print("Scaling factor used: " + str(scaling_factor))
    band['r_400'] = imageIn[:,:,0].astype(float)/scaling_factor
    band['r_550'] = imageIn[:,:,1].astype(float)/scaling_factor
    band['r_670'] = imageIn[:,:,2].astype(float)/scaling_factor
    band['r_710'] = imageIn[:,:,3].astype(float)/scaling_factor
    band['r_800'] = imageIn[:,:,4].astype(float)/scaling_factor
    #band['r_670'][band['r_670']==0]=1



    #Clean up some ram
    del imageIn

    #rotate and crop file to just plot area
    band,plots,textlocation,corners  = rotateAndCrop(band,shapefilename,TiePoint,scale) 
    
    # #Create And Calculate Coverage
    print('Making Masks:')
    masks = {}
    maskThreshold = {}
    maskname = plantcountinidicechoice
    TempMask = indice_calculation(band,maskname)
    createimage(TempMask,plots,maskname,textlocation)
    creategridimage(TempMask,plots,maskname,textlocation)
    TempMask = (TempMask*(255)).astype(np.uint8)
    if(MaskOtsu == True):
        (T, masks[maskname]) = cv2.threshold(TempMask, 0, 255,cv2.THRESH_OTSU+cv2.THRESH_BINARY_INV)
    else:
        (T, masks[maskname]) = cv2.threshold(TempMask, (masklevels*255), 1,cv2.THRESH_OTSU)

    
    print('Plant Counting')
        #polygon codes for count
    codes = [             
        path.Path.MOVETO,
        path.Path.LINETO,
        path.Path.LINETO,
        path.Path.LINETO,
        path.Path.CLOSEPOLY,
        ]
    plancountfile = open(results_location+"/plant_count.csv",'w')
    plancountfile.write('plot,plantNo\n')
    params = cv2.SimpleBlobDetector_Params()
    params.filterByCircularity = False;
    params.filterByConvexity = False;
    params.filterByInertia = False;
    params.filterByArea = True;
    params.minArea = min_area;
    params.minDistBetweenBlobs = min_distance;
    detector = cv2.SimpleBlobDetector_create(params)
    
    
    
    
    keypoints = detector.detect(masks[maskname])
    locationpts = cv2.KeyPoint_convert(keypoints)
    createimageplantcount(masks[maskname],plots,'otsu',textlocation,keypoints)
    for plot in plots:
        plotPath = path.Path([[corners[plot][0],corners[plot][2]],
                                [corners[plot][1],corners[plot][2]],
                                [corners[plot][1],corners[plot][3]],
                                [corners[plot][0],corners[plot][3]],
                                [corners[plot][0],corners[plot][2]]],
                                codes)
        plotcount = path.Path.contains_points(plotPath,(locationpts))
        plancountfile.write('{0:s},{1:d}\n'.format(plot,(len(plotcount[plotcount==True]))))
   
    ground = {}
    print('Calculating Ground')
    if 'heights' in band.keys():
        for plot in plots:
            plotData={}
            plotData['heights'] = band['heights'][(corners[plot][2]):(corners[plot][3]),(corners[plot][0]):(corners[plot][1])]
            ground[plot] = np.percentile(plotData['heights'],2)
        return ground
    else:
        return 0
        #do full plot
               
def writeDatatoFile(value,plot,indice,variableType,mask,threshold):
    #'trial,date,time,flight_height,sensor,plot_id,variable,value\n'
    if mask =='no mask':
        variable = '{0:s}_{1:s}_{2:s}'.format(variableType,indice,mask)
    else:
        variable = '{0:s}_{1:s}_{2:.5f}<{3:s}<=1.0'.format(variableType,indice,threshold,mask)
    output.write('{0:s},{1:s},{2:s},{3:s},{4:s},{5:s},{6:s},{7:f}\n'.format(trial_v,date_v,time_v,height_v,camera_v,plot,variable,value))
#Calculate the values from the polts as rotated can assume square(Must make more robust for other shapes)        
def CalculateCoverage(data,plots,indice,corners):
    for plot in plots:
            plotData = data[(corners[plot][2]):(corners[plot][3]),(corners[plot][0]):(corners[plot][1])]
            coverage = np.sum(plotData)/plotData.size
            writeDatatoFile(coverage,plot,indice,'Coverage','no mask','no threshold')
                    
def createimage(data,plots,plotname,textlocation):
    img = (data*(255/np.nanmax(data))).astype(np.uint8)
    img = cv2.applyColorMap(img,cv2.COLORMAP_RAINBOW)
    for plot in plots:
        img = cv2.polylines(img,[plots[plot]],True,(0,0,0)) 

        font = cv2.FONT_HERSHEY_SIMPLEX
        img = cv2.putText(img, plot, textlocation[plot], font,0.4, (0,0,0), 2, cv2.LINE_AA)
        img = cv2.putText(img, plot, textlocation[plot], font,0.4, (255,255,255), 1, cv2.LINE_AA)
    cv2.imwrite((results_location+'/'+ plotname +'_'+date_v+ '.png'),img)
    
    
def createimageplantcount(data,plots,plotname,textlocation,keypoints):
    img = (data*(255/np.nanmax(data))).astype(np.uint8)
    img = cv2.applyColorMap(img,cv2.COLORMAP_BONE)
    img = cv2.drawKeypoints(img, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    for plot in plots:
        img = cv2.polylines(img,[plots[plot]],True,(0,0,255)) 

        font = cv2.FONT_HERSHEY_SIMPLEX
        img = cv2.putText(img, plot, textlocation[plot], font,0.4, (0,0,0), 2, cv2.LINE_AA)
        img = cv2.putText(img, plot, textlocation[plot], font,0.4, (255,255,255), 1, cv2.LINE_AA)
    cv2.imwrite((results_location+'/'+ plotname +'_'+date_v+ '.png'),img)
def createimagesingleplot (data,plot):
    img = (data*(255/np.nanmax(data))).astype(np.uint8)
    img = cv2.applyColorMap(img,cv2.COLORMAP_RAINBOW)
    font = cv2.FONT_HERSHEY_SIMPLEX
    img = cv2.putText(img, plot, (0,0), font,0.4, (0,0,0), 2, cv2.LINE_AA)
    img = cv2.putText(img, plot, (0,0), font,0.4, (255,255,255), 1, cv2.LINE_AA)
    cv2.imwrite((results_location+'/single_image/'+ plot +'_'+date_v+ '.png'),img)

    
def creategridimage(data,plots,plotname,textlocation):
    img = np.ones([data.shape[0],data.shape[1],3])
    img = (img*255).astype(np.uint8)
    for plot in plots:
        img = cv2.polylines(img,[plots[plot]],True,(0,0,255)) 

        font = cv2.FONT_HERSHEY_SIMPLEX
        img = cv2.putText(img, plot, textlocation[plot], font,0.4, (0,0,0), 2, cv2.LINE_AA)
        img = cv2.putText(img, plot, textlocation[plot], font,0.4, (255,255,255), 1, cv2.LINE_AA)
    cv2.imwrite((results_location+'/grid.png'),img)
    
def rotateAndCrop(bands,shapefilename,TiePoint,scale) :
    plot_lower_left = {}
    lowest_left_corner = (bands['r_400'].shape[1],bands['r_400'].shape[0])
    highest_right_corner = (0,0)
    lowest_right_corner = (bands['r_400'].shape[1],bands['r_400'].shape[0])
    highest_left_corner = (0,0)    
    #find corners for the plots
    with shapefile.Reader(shapefilename) as shp:
        for plot in shp.shapeRecords():               
            polygon = [((i[0]- TiePoint[3])/scale[0],(i[1]- TiePoint[4])/-scale[1]) for i in plot.shape.points[:]]              
            record = plot.record
            #find centre of polygon
            x,y=zip(*polygon)
            #find left extents             
            temp_left_corner = (np.min(x),y[x.index(np.min(x))])
            if temp_left_corner[0] < lowest_left_corner[0]:
                lowest_left_corner = temp_left_corner
            plot_lower_left[record['Plot_ID']]=temp_left_corner
            temp_left_corner = (np.max(x),y[x.index(np.max(x))])
            if temp_left_corner[0] > highest_left_corner[0]:
                highest_left_corner = temp_left_corner
            #find right extents
            temp_right_corner = (x[y.index(np.max(y))],np.max(y))
            if temp_right_corner[1] > highest_right_corner[1]:
                highest_right_corner = temp_right_corner                 
            temp_right_corner = (x[y.index(np.min(y))],np.min(y))
            if temp_right_corner[1] < lowest_right_corner[1]:
                lowest_right_corner = temp_right_corner
    extents = np.array([lowest_left_corner,lowest_right_corner,highest_left_corner,highest_right_corner,lowest_left_corner],dtype=np.int32)    
    #Calculate rotation angle
    image_angle_rad = np.arctan2(lowest_right_corner[1] - lowest_left_corner[1],lowest_right_corner[0] - lowest_left_corner[0])
    #print(image_angle_rad)
    M=cv2.getRotationMatrix2D(lowest_left_corner,np.rad2deg(image_angle_rad),1)
    rect = cv2.boundingRect(extents)
    x,y,w,h = rect
    endBound = rotate(lowest_left_corner, highest_left_corner, -image_angle_rad)
    X1 = np.int32(lowest_left_corner[0])
    Y1 = np.int32(lowest_left_corner[1]) 
    X2 = np.int32(endBound[0])
    Y2 = np.int32(endBound[1]) 
    newextents = np.array([[X1,Y1],[X2,Y1],[X2,Y2],[X1,Y2],[X1,Y1]],dtype=np.int32)
    #create new array
    for singleBand in bands: 
        bands[singleBand] = cv2.warpAffine(bands[singleBand],M,(X2+PlotBuffer,Y2+PlotBuffer))
        bands[singleBand] = bands[singleBand][(Y1-PlotBuffer):(Y2+PlotBuffer),(X1-PlotBuffer):(X2+PlotBuffer)]
        
    #thermalimg = (bands['thermal']*(255/np.nanmax(bands['thermal']))).astype(np.uint8)
    #thermalimg = cv2.applyColorMap(thermalimg,cv2.COLORMAP_JET)
    plotdic = {}
    textlocation = {}
    corners = {}
    with shapefile.Reader(shapefilename) as shp:        
        for plot in shp.shapeRecords():
            #try:
                
                polygon = [rotateint((PlotBuffer,PlotBuffer),((i[0]- TiePoint[3])/scale[0]-lowest_left_corner[0]+PlotBuffer,(i[1]- TiePoint[4])/-scale[1]-lowest_left_corner[1]+PlotBuffer),-image_angle_rad) for i in plot.shape.points[:]]
                #y = [(i[1]- TiePoint[4])*-scale[1] for i in plot.shape.points[:]]                
                record = plot.record                
                pts = np.array(polygon, np.int32)
                pts = pts.reshape((-1,1,2))
                plotdic[record['Plot_ID']] = pts
                x,y=zip(*polygon)
                # cv2.polylines(thermalimg,[pts],True,(0,0,255))                    
                textlocation[record['Plot_ID']]=np.int32((np.min(x)+5)), np.int32((np.max(y)+np.min(y))/2)
                corners[record['Plot_ID']]=[np.min(x),np.max(x),np.min(y),np.max(y)]
                # font = cv2.FONT_HERSHEY_SIMPLEX
                # thermalimg = cv2.putText(thermalimg, record['Plot_ID'], center, font,0.4, (0,0,0), 2, cv2.LINE_AA)
                # thermalimg = cv2.putText(thermalimg, record['Plot_ID'], center, font,0.4, (255,255,255), 1, cv2.LINE_AA)
    #cv2.imwrite((results_location+'/thermal.png'),thermalimg)
    return bands,plotdic,textlocation,corners
    
    
        
    
def indice_calculation(band,index_name):

    if (index_name == "ndvi"):
        v = np.divide((band["r_800"] - band["r_670"]) , (band["r_800"] + band["r_670"]))
    elif (index_name == "ndre_r"): 
        v = np.divide((band["r_800"] - band["r_710"]) , (band["r_800"] + band["r_710"]))
    elif (index_name == "dvi"):   
            v = band["r_800"] - band["r_670"]
    
    elif (index_name == "evi"):
        v = 2.5 * np.divide((band["r_800"] - band["r_670"]) , (band["r_800"] + 6 * band["r_670"] - 7.5 * band["r_400"] + 1))
    elif (index_name == "endvi"):     
        v = np.divide(((band["r_800"] + band["r_550"]) - (band["r_400"] * 2.0)) ,((band["r_800"] + band["r_550"]) + (band["r_400"] * 2.0)))
    elif (index_name == "exg"):
        rgb_sum = band["r_670"] + band["r_550"] + band["r_400"]
        v = 2.0 * (band["r_550"] / rgb_sum) - (band["r_670"] / rgb_sum) - (band["r_400"] / rgb_sum)
    elif (index_name == "gemi"):
        n = np.divide((2.0 * ((band["r_800"]** 2.0) - (band["r_670"]** 2.0)) + 1.5 * band["r_800"] + 0.5 * band["r_670"]) , (band["r_800"] + band["r_670"] + 0.5))
        v = n * (1.0 - 0.25 * n) - np.divide((band["r_670"] - 0.125) , (1.0 - band["r_670"]))
    elif (index_name == "gari"):
        v = np.divide((band["r_800"] - (band["r_550"] - (band["r_400"] - band["r_670"]))) , (band["r_800"] + (band["r_550"] - (band["r_400"] - band["r_670"]))))
    elif (index_name == "clg"):
        v = np.divide(band["r_800"] , band["r_550"]) - 1.0
    elif (index_name == "gdvi"):
        v = band["r_800"] - band["r_550"]
    elif (index_name == "gli"):
        rgb_sum = band["r_670"] + band["r_550"] + band["r_400"]
        v = np.divide((2.0 * (band["r_550"] / rgb_sum) - (band["r_670"] / rgb_sum) - (band["r_400"] / rgb_sum)) ,(2.0 * (band["r_550"] / rgb_sum) + (band["r_670"] / rgb_sum) + (band["r_400"] / rgb_sum)))
    elif (index_name == "gndvi"):
        v = np.divide((band["r_800"] - band["r_550"]) , (band["r_800"] + band["r_550"]))
    elif (index_name == "grvi"):
        v = np.divide(band["r_800"] , band["r_550"])
    elif (index_name == "gsavi"):
        v = np.divide(((band["r_800"] - band["r_550"]) , (band["r_800"] + band["r_550"] + 0.5))) * 1.5
    elif (index_name == "msavi2"):
        v = (2.0 * band["r_800"] + 1.0 - np.sqrt(((2.0 * band["r_800"] + 1.0)** 2.0) - 8.0 * (band["r_800"] - band["r_670"]))) / 2.0
    elif (index_name == "ng"):
        v = np.divide(band["r_550"] , (band["r_800"] + band["r_670"] + band["r_550"]))
    elif (index_name == "nnir"):
        v = np.divide(band["r_800"] , (band["r_800"] + band["r_670"] + band["r_550"]))
    elif (index_name == "nr"):
        v = np.divide(band["r_670"] , (band["r_800"] + band["r_670"] + band["r_550"]))
    elif (index_name == "osavi"):
        v = np.divide((band["r_800"] - band["r_670"]) , (band["r_800"] + band["r_670"] + 0.16)) * 1.16
    elif (index_name == "rvi"):
        v = np.divide(band["r_800"] , band["r_670"])
    elif (index_name == "clre"):
        v = np.divide(band["r_800"] , band["r_710"]) - 1.0
    elif (index_name == "rendvi"):
        v = (band["r_800"] - band["r_710"]) / (band["r_800"] + band["r_710"])
    elif (index_name == "savi"):
        v = (np.divide((band["r_800"] - band["r_670"]) , (band["r_800"] + band["r_670"] + 0.5))) * 1.5
    elif (index_name == "varigreen"):
        v = np.divide((band["r_550"] - band["r_670"]) , (band["r_550"] + band["r_670"] - band["r_400"]))
    elif (index_name == "vigreen"):
        v = np.divide((band["r_550"] - band["r_670"]) , (band["r_550"] + band["r_670"]))
    elif (index_name == "temperature"):
        v = band['thermal']
    elif (index_name == "heights"):
        v = band['heights']
    return v    
    
def rotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point
    c = np.cos(angle)
    s = np.sin(angle)
    px = px - ox
    py= py-oy
    qx = px*c-py*s+ox
    qy = px*s+py*c+oy
    return qx, qy

def rotateint(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point
    c = np.cos(angle)
    s = np.sin(angle)
    px = px - ox
    py= py-oy
    qx = px*c-py*s+ox
    qy = px*s+py*c+oy
    return np.int32(qx), np.int32(qy)   
    
    
    
def main(input_location,shapefile_location,first_file) :


#    tif_file = "DAF_hermitage_wheat-3_2020-10-16_14-46-00_altum_bgreni_25m_transparent_reflectance_packed.tif"


    try:
        os.mkdir(results_location)
    except(OSError):
        print('Results folder already exists')
    global output
    #get trial name from plot ID
    shp = shapefile.Reader(shapefile_location)
    record= shp.record(1)
    print(record['Plot_ID'])
    firstplot = record['Plot_ID']
    trialnamefromshape = firstplot.split('_')
    
    output = open(results_location+"/data_"+trialnamefromshape[0]+".csv",'w')
    output.write('trial,date,time,flight_height,sensor,plot_id,variable,value\n')
    print(input_location)
    
    if (first_file!='none'):
        print('Processing Emergence')
        ground  = processemergencedata(first_file,shapefile_location,input_location)
    else:
        ground = 0
    for tif_file in glob.glob(input_location+'/*.tif'):
        print(tif_file)
        process_file(tif_file,shapefile_location,output,first_file,input_location,ground)
    output.close()

    
    #for las_file in glob.glob(input_location+'/*.las'):
    #    print(las_file)
    #    process_las(las_file,shapefile_location,results_location)
        
    

# Plant_count (Yes or No) #################### TO DO ###############################

# Initial DEM?? ###################### TO DO #############################
# MS DEM location
dem_location = os.getcwd() + '\\output\\DEM\\MS'

if __name__ == "__main__":
    first_file = 'UQ_GilbertN_danNVT_2022-07-11_10-00-00_Altum_bgren_20m_transparent_reflectance_packed.tif'
    global results_location
    input_location = os.getcwd() + '\\output\\ortho\\MS'
    shapefile_location = os.path.dirname(os.getcwd()) + shp_filename
    results_location = os.getcwd() + '\\output\\XtractoR_Output'

    main(input_location,shapefile_location,first_file)    


# In[ ]:




