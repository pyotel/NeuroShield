## Simple Imaging test
## copyright(c) 2018 General Vision

import sys
import ctypes
import NeuroMem as nm
import GVcomm_SPI as comm
#import matplotlib.pyplot as plt
import cv2 as cv

LENGTH=256
bytearray = ctypes.c_int * LENGTH
vector=bytearray()

#----------------------------------------------
# Scan a region of scan (ROS) with a step XY
# recognize a region of interest at each position
# return the list of XY positions where a known pattern
# was recognized by the neurons and which category was recognized
#----------------------------------------------
def surveyROS(image, rosL, rosT, rosW, rosH, stepX, stepY):
  objNbr=0
  ctrX=[]
  ctrY=[]
  cats=[]
  for y in range(rosT, rosT + rosH - roiH, stepY):
    for x in range(rosL, rosL + rosW - roiW, stepX):
      vlen, vector =GetGreySubsample(image, x, y, roiW, roiH, bW, bH, normalize)
      dist, cat, nid = nm.BestMatch(vector, vlen)
      if (dist!=0xFFFF):
        # If the neurons recognize something
        # store the center position of the recognized ROI and its recognized category
        ctrX.append(int(x + roiW/2))
        ctrY.append(int(y + roiH/2))
        cats.append(cat)
        objNbr=objNbr+1
  return(objNbr, ctrX, ctrY, cats)
#-----------------------------------------------------
# Extract a subsample of the ROI at the location X,Y
# using a block size bW*bH and amplitude normalization on or off
# return the length of the output vector
#-----------------------------------------------------
def GetGreySubsample(image, roiL, roiT, roiW, roiH, bW, bH, normalize):
  # subsample blocks of BWxBH pixels from the ROI [Left, Top, Width, Height]
  # vector is the output to broadcast to the neurons for learning or recognition
  p = 0
  for y in range(roiT, roiT + roiH, bH):
    for x in range(roiL, roiL + roiW, bW):
      Sum=0	
      for yy in range(0, bH):
        for xx in range (0, bW):
          # to adjust if monochrome versus rgb image array
          Sum += image[y+yy, x+xx]
      vector[p] = (int)(Sum / (bW*bH))

      #log the min and max component
      min = 255
      max = 0
      if (max < vector[p]):
        max = vector[p]
      if (min > vector[p]):
        min = vector[p]
      p=p+1
    
  if ((normalize == 1) & (max > min)):
    for i in range (0, p):
      Sum= (vector[i] - min) * 255
      vector[i] = (int)(Sum / (max - min))

  # return the length of the vector which must be less or equal to 256
  return p, vector

#-------------------------------------------------
# Select a NeuroMem platform
# 0=simu, 1=NeuroStack, 2=NeuroShield, 4=Brilliant
#-------------------------------------------------
if (comm.Connect()!=0):
  print ("Cannot connect to NeuroShield\n")
  sys.exit()

nm.ClearNeurons()

# Load an image for analysis
imsrc=cv.imread('face.jpg')
cv.imshow('Image Source', imsrc)
cv.waitKey(3)

imgl = cv.cvtColor(imsrc, cv.COLOR_BGR2GRAY)
imW=imgl.shape[1]
imH=imgl.shape[0]
print("Image = " + repr(imW) + " x " + repr(imH))
imCtrX= imW/2
imCtrY= imH/2

roiW = int(64)
roiH = int(64)
roiL= int(imCtrX - roiW/2)
roiT= int(imCtrY - roiH/2)
bW = int(4)
bH = int(4)
normalize = int(1)

# prepare image to hold the ROI overlay
imdisp=imgl.copy()
cv.rectangle(imdisp,(roiL, roiT),(roiL+roiW, roiT+roiH),(255,0,0),1)
cv.imshow('Learn central ROI', imdisp)
cv.waitKey(3)

# Learn ROI at center of the image
vlen, vector=GetGreySubsample(imgl, roiL, roiT, roiW, roiH, bW, bH, normalize)
nm.Learn(vector,vlen,1)

# Learn a counter example ROI at an offset of 10 pixels right and down
vlen, vector=GetGreySubsample(imgl, roiL + 10, roiT + 10, roiW, roiH, bW, bH, normalize)
ncount = nm.Learn(vector,vlen,0)
print("ncount =" + repr(ncount))

# Recognize ROI at same position, expect a distance of 0
vlen, vector =GetGreySubsample(imgl, roiL, roiT, roiW, roiH, bW, bH, normalize)
dist, cat, nid = nm.BestMatch(vector, vlen)
print("Reco cat = " + repr(cat) + " at dist =" + repr(dist))

# Recognize ROI at an offset of 5 pixels left and down, expect a distance > 0
vlen, vector =GetGreySubsample(imgl, roiL + 5, roiT + 5, roiW, roiH, bW, bH, normalize)
dist, cat, nid = nm.BestMatch(vector, vlen)
print("Reco cat = " + repr(cat) + " at dist =" + repr(dist))

# Recognize ROI at an offset of 12 pixels left and down, expect a distance 0xFFFF
# due to counter example taught at offset =10
vlen, vector =GetGreySubsample(imgl, roiL + 12, roiT + 12, roiW, roiH, bW, bH, normalize)
dist, cat, nid = nm.BestMatch(vector, vlen)
print("Reco cat = " + repr(cat) + " at dist =" + repr(dist))

# Look for similar ROI over a larger ROS (Region Of Search) representing
# one third of the whole image and centered in the image
rosW= int(imW/3)
rosH= int(imH/3)
rosL= int(imCtrX - rosW/2)
rosT= int(imCtrY - rosH/2)
stepX = 4
stepY = 4
objNbr, posX, posY, cats =surveyROS(imgl, rosL, rosT, rosW, rosH, stepX, stepY)

# prepare image to display ROS + object overlay
imdisp2= imgl.copy()
cv.rectangle(imdisp2, (rosL,rosT),(rosL+rosW, rosT+rosH),(255,0,0),1)
cv.imshow('Scan ROS', imdisp2)
cv.waitKey(3)

print("Recognized objects: " + repr(objNbr))
for i in range (0,objNbr):
  cv.circle(imdisp2,(posX[i],posY[i]), 1, (0,0,255), -1)
#   print("PosX " + repr(posX[i]) + " PosY=" + repr(posY[i]))
cv.imshow('Recognized Objects', imdisp2)
cv.waitKey(0)

# Calculate center of gravity of the recognized locations
# to send to the motion control
