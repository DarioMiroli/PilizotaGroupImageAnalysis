"""Mix of functions used for image processing and data extraction."""
import numpy as np
from scipy import ndimage as ndi
from scipy import misc
import scipy.fftpack
import os
import platform
import pickle
import matplotlib
if platform.system() == 'Linux':
    matplotlib.use("GTKAgg")
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import LogNorm
from matplotlib.ticker import MultipleLocator

from skimage.filters import *
from skimage.morphology import *
from skimage import measure
from skimage import segmentation
from skimage import io
from skimage import exposure
from skimage.measure import *
from skimage.feature import peak_local_max

from matplotlib.widgets import  RectangleSelector
from pylab import *

import tifffile as tif

#Custom classes
from AnnotateImage import Annotate

def Setup(inputFolder, outputFolder):
    '''
    Creates output folder if it doesnt exist and get input file names from input
    file.
    '''
    try:
        os.stat(outputFolder)
    except:
        os.mkdir(outputFolder)
    filenames = os.listdir(inputFolder+"/")
    return filenames

def CreateFolder(folderName):
    '''
    Crates folder if it doens not already exist.
    '''
    try:
        os.stat(folderName)
    except:
        os.mkdir(folderName)

def GetFileNamesFromFolder(path,fileOnly = True):
    '''
    Retrives all names of files in folder
    '''
    filenames = os.listdir(path+"/")
    if fileOnly:
        return filenames
    else:
        folderAndNames = []
        for f in filenames:
            folderAndNames.append(os.path.join(path,f))
        return folderAndNames

def StripImageFiles(fileNames, OKExtensions =["tiff","tif"]):
    '''
    Removes files with the wrong extension from a list of files
    '''
    acceptedFiles = []
    for f in fileNames:
        if f.split(".")[-1] in OKExtensions:
            acceptedFiles.append(f)
    return acceptedFiles

def Open(pathname):
    '''
    Returns numpy array of image at pathname.
    '''
    Image = ndi.imread(pathname)
    Image_Array = np.array(Image)
    return(Image_Array)

def ShowMe(image, cmap=plt.cm.gray):
    '''
    Shows the given image at runtime
    '''
    plt.imshow(image, cmap=cmap,interpolation='none')
    if len(np.shape(image)) < 2: plt.colorbar()
    plt.show()

def SelectReigon(image,bgColor='blue',title=""):
    ''' Selects reigon of image with mouse clicks'''
    plt.imshow(image)
    a = Annotate(bgColor)
    plt.title(title)
    plt.show()
    rects = a.getRects()
    del a
    return rects

def CompareAnnotate(images,bgColor='blue',ColorBarArray=None, TitleArray=None,
        commonScaleBar=True, axX=1,axY=1,mode='Recs',data=None):
    '''Allows annotation of multiple compared images'''
    ax = Compare(images,ColorBarArray=ColorBarArray,TitleArray=TitleArray,
            commonScaleBar=commonScaleBar, show=False)
    a = Annotate(bgColor,ax=ax[axX][axY],mode='Rmv',data=data)
    plt.title(title)
    plt.show()
    finalData = a.getData()
    del a
    return finalData

def Crop(image,rectangle):
    '''Crops image using bounding box '''
    rectangle = np.asarray(rectangle,int)
    x1,x2,y1,y2 = MouseToImageCoords(rectangle)
    croppedImage = image[x1:x2,y1:y2]
    return(croppedImage)

def MouseToImageCoords(rectangle):
    ''' Converts mouse coordinates to image coordinates'''
    if rectangle[2] > rectangle[3]:
        x1 = rectangle[3]
        x2 = rectangle[2]
    else:
        x1 = rectangle[2]
        x2 = rectangle[3]
    if rectangle[0] > rectangle[1]:
        y1 = rectangle[1]
        y2 = rectangle[0]
    else:
        y1 = rectangle[0]
        y2 = rectangle[1]
    return x1,x2,y1,y2

def Blurr(image,sigma=1.0,imageType='RGB'):
    '''
    Perofrms a gaussian blurr on Image with standard deviation sigma.
    '''
    blurredImage = np.zeros(np.shape(image))
    if imageType == 'RGB':
        for layer in range(np.shape(image)[2]):
            blurredImage[:,:,layer] =  gaussian_filter(image[:,:,layer],sigma=sigma)
    if imageType == "sequence":
        for im in range(np.shape(image)[2]):
            blurredImage[:,:,im] =  gaussian_filter(image[:,:,im],sigma=sigma)
    if imageType == "gray":
        blurredImage =  gaussian_filter(image,sigma=sigma)
    return(blurredImage)

def Threshold(Image,blockSize):
    '''
    Performs an adaptive threshold on Image. Threshold value is obtained by
    averaging pixels in each small reigon the size of which is given by
    blocksize.
    '''
    Threshold_Image = threshold_adaptive(Image, blockSize)
    return(Threshold_Image)

def GlobalThreshold(Image,threshold=None):
    '''
    Simple threshold of image using single threshold value over whole image.
    '''
    if threshold == None:
        threshold = threshold_otsu(Image)
    Image = Image > threshold
    return(Image*1)

def Erode(Image,numberoftimes):
    '''
    Performs binary erosion of image a required number of times.
    '''
    for i in range(numberoftimes):
        Image = binary_erosion(Image)
    return(Image)

def Dilate(Image,numberoftimes):
    '''
    Performs binary dilation on Image a required number of times.
    '''
    for i in range(numberoftimes):
        Image = binary_dilation(Image)
    return(Image)

def DistanceTransform(Image):
    '''
    Takes distance transform of image.
    '''
    return(ndi.distance_transform_edt(Image))

def Label(Image):
    '''
    Labels each connected reigon in Image with a different number
    '''
    Labelled_Image = measure.label(Image, background=0,connectivity =2)
    return(Labelled_Image)

def ClearBorders(Image):
    '''
    Removes objects connected to image edges
    '''
    labeled = Image - np.amin(Image)#measure.label(Image,connectivity =2)
    return segmentation.clear_border(labeled)+np.amin(Image)

def BboxImages(Image,mask):
    '''
    Returns a vounding box image for each label in an image
    '''
    bBoxedImages = []
    bBoxedMasks = []
    l = Label(mask)
    props = measure.regionprops(l)
    print("props",len(props))
    for prop in props:
        x1,y1,x2,y2 = prop.bbox
        bBoxedImages.append(Image[x1-10:x2+10,y1-10:y2+10])
        bBoxedMasks.append(mask[x1-10:x2+2,y1-10:y2+10])
    return bBoxedImages, bBoxedMasks

def GetSebLength(Image,count):
    #Tidy up iamge for analysis. Clear it flip it if necessary
    cleared = ClearBorders(Image)
    cleared = cleared-np.amin(cleared)
    props = measure.regionprops(cleared)
    x1,y1,x2,y2 = props[0].bbox
    box = cleared[x1:x2,y1:y2]
    width , height = box.shape
    if width > height:
        box = np.swapaxes(box,0,1)
        width , height = box.shape

    #Compute all points on top and bottom of cell
    topPoints= []
    bottomPoints = []
    for y in range(height):
        topIntersection = None
        bottomIntersection = None
        for x in range(width):
            if box[x][y] > 0 and topIntersection == None:
                topIntersection = x
            if box[width-1-x][y] > 0 and bottomIntersection == None:
                bottomIntersection = width-1-x
        topPoints.append([topIntersection,y])
        bottomPoints.append([bottomIntersection,y])
        #plt.plot(y,topIntersection,'*',color='g',markersize=25)
        #plt.plot(y,bottomIntersection,'*',color='y',markersize=25)

    #Get edge points in order
    normBox = ((box-np.amin(box))/np.amax(box))
    edgeImage =  np.pad(normBox - Erode(normBox,1),0,'constant')
    xedgePixels, yedgePixels = np.where(edgeImage>0)

    #Order Edge Points
    orderedEdgePoints = []
    ys = list(np.arange(height)) + list(np.arange(height,0,-1))
    for delta in [1,-1]:
        for y in range(height):
            tempPoints = []
            on = False
            off = False
            if np.sum(edgeImage[:,y]) >2:
                for x in range(width):
                    if edgeImage[delta*x][y] > 0:
                        on = True
                    if edgeImage[delta*x][y] == 0 and on:
                        off = True
                    if on and not off and edgeImage[delta*x][y]>0:
                        if delta == 1:
                            tempPoints.append([x,y])
                        if delta!=1 and y!=0:
                            tempPoints.append([width-x,y])
                if y>0:
                    if tempPoints[0][1] < orderedEdgePoints[-1][0]:
                        tempPoints = tempPoints[::-1]
                else:
                    tempPoints = tempPoints[::-1]
                orderedEdgePoints = orderedEdgePoints+ tempPoints
            else:
                for x in range(width):
                    if edgeImage[delta*x][y] > 0:
                        if delta == 1:
                            orderedEdgePoints = orderedEdgePoints + [[x,y]]
                            break
                        else:
                            if x != 0:
                                orderedEdgePoints = orderedEdgePoints + [[width-x,y]]
                                break
        orderedEdgePoints= orderedEdgePoints[::-1]
    #Remove duplicates
    newOEPoints = []
    for i in range(len(orderedEdgePoints)):
        if not (orderedEdgePoints[i] in orderedEdgePoints[0:i]):
            newOEPoints.append(orderedEdgePoints[i])
    orderedEdgePoints = newOEPoints
    orderedXs = [orderedEdgePoints[i][0] for i in range(len(orderedEdgePoints))]
    orderedYs = [orderedEdgePoints[i][1] for i in range(len(orderedEdgePoints))]

    #plt.clf()
    #plt.imshow(edgeImage,interpolation='None')
    #plt.scatter(orderedYs,orderedXs,c=np.arange(len(orderedXs)))
    #plt.show()
    #plt.clf()

    #Find mid index
    midPoint = np.argmin(np.abs(np.asarray(orderedYs)-height/2.0))

    #Run around cell from mid index calcing curvature
    curveLength = 10
    curvatures = []
    plt.ion()
    for i in range(midPoint,len(orderedEdgePoints)+midPoint):
        plt.imshow(edgeImage,interpolation='None')
        plt.plot(orderedYs[i-curveLength:(i+curveLength)%len(orderedEdgePoints)+1],
                orderedXs[i-curveLength:(i+curveLength)%len(orderedEdgePoints)+1],
                'o-')
        x1 = orderedXs[(i-curveLength)%len(orderedEdgePoints)]
        x2 = orderedXs[(i+curveLength)%len(orderedEdgePoints)]
        y1 = orderedYs[(i-curveLength)%len(orderedEdgePoints)   ]
        y2 = orderedYs[(i+curveLength)%len(orderedEdgePoints)]
        dist = ( (x2-x1)**2 + (y2-y1)**2 )**0.5
        #dist = abs(x2-x1) + abs(y2-y1)
        curvatures.append(dist)
        #plt.title(dist)
        #plt.pause(0.0001)
        #plt.clf()

    #clear up figure
    plt.ioff()
    plt.close()
    plt.clf()

    #Mark polls
    leftData = curvatures[0:len(curvatures)//2]
    leftPole = np.argmin(leftData)
    rightData = curvatures[len(curvatures)//2:]
    rightPole = np.argmin(rightData)

    #Smooth with ft
    w = scipy.fftpack.rfft(curvatures)
    spectrum = w**2
    cutoff_idx = spectrum < (spectrum.max()/50000)
    w2 = w.copy()
    w2[cutoff_idx] = 0
    y2 = scipy.fftpack.irfft(w2)
    leftPole2 = np.argmin(y2[0:len(curvatures)//2])
    rightPole2 = np.argmin(y2[len(curvatures)//2:])

    #Create skeleton with poles added
    BackBone = Skeletonize(normBox)
    BackBone[orderedXs[leftPole2+midPoint] , orderedYs[leftPole2+midPoint]] = 1
    BackBone[orderedXs[(rightPole2+midPoint+len(curvatures)//2)%len(orderedXs)],
            orderedYs[(rightPole2+midPoint+len(curvatures)//2)%len(orderedYs)]]=1
    newImage,ydata,xdata,zs= FitSkeleton(np.transpose(BackBone))
    plt.ion()
    plt.imshow(normBox,interpolation='None')
    plt.plot(ydata,xdata)
    plt.title(count)
    plt.pause(0.01)
    plt.clf()




def GetArea(Image):
    '''
    Get area from binary mask
    '''
    props = measure.regionprops(Image)
    area = None
    for prop in props:
        if prop.label !=1:
            area = prop.area
    return area

def WaterShed(Image):
    '''
    Performs water shed transform on Image. Useful for segmentation of connected
    reigons.
    '''
    Distance_Transformed_Image = DistanceTransform(Image)
    Local_Maxima = peak_local_max(Distance_Transformed_Image, indices=False, footprint=np.ones((5, 5)),labels=Image)
    markers = measure.label(Local_Maxima)
    Watershed_Image = watershed(-Distance_Transformed_Image, markers, mask=Image)
    return(Watershed_Image)

def Skeletonize(Image):
    '''
    Reduces Image to a skeleton.
    '''
    Image = (Image - np.amin(Image))/np.amax(Image)
    return(skeletonize(Image)*1)

def ComputePoly(x,zs):
    '''
    Computes y value from given x value and polynomial coefficients
    '''
    deg = len(zs)-1
    y=0
    for n in range(deg+1):
        y += zs[deg-n]*x**n
    return y

def FitSkeleton(Image,degree=2):
    ''' Returns image with fitted polynomial to given skeleton
    '''
    coords = (np.where(Image>0))
    xs = coords[0]
    ys = coords[1]
    zs = np.polyfit(xs,ys,degree)
    width , height = Image.shape
    newImage = np.zeros((width,height))
    for x in range(width):
        y = ComputePoly(x,zs)
        y=int(y)
        if y>=height: y = height -1
        if y< 0: y = 0
        newImage[x,y] =1

    xdata = np.arange(0,width,0.1)
    ydata = [ComputePoly(x,zs) for x in xdata]
    ydata = np.clip(ydata,0,height)
    return newImage,xdata,ydata,zs

def getCellLength(Image,zs):
    if len(zs) == 2:
        started = False
        width,height = Image.shape
        startPoint = -1
        endPoint =-1
        for x in range(width):
            y = ComputePoly(x,zs)
            if y>=height: y = height -1
            if y< 0: y = 0
            if Image[x,y] > 0 and not started:
                startPoint = [x,y]
                started = True
            if Image[x,y] > 0 and started:
                endPoint = [x,y]
        if startPoint != -1 and endPoint != -1:
            cellLength = ((1+zs[0]**2)**0.5)*(endPoint[0]-startPoint[0])
        else:
            cellLength = -1
    else:
        print("Not polynomial fit")
        exit()
    return cellLength

def SiveArea(Image,smallest=0,largest=1E9):
    '''
    Removes connected reigons smller than smallest and larger than largest in
    Image.
    '''
    Image = np.copy(Image)
    BadReigons = []
    for reigon in measure.regionprops(Image):
        if reigon.area > largest or reigon.area < smallest:
            BadReigons.append(reigon.label)
    for i in BadReigons:
        Image[Image==i] = 0
    Image,a,b = segmentation.relabel_sequential(Image)
    return(Image)

def Centering(thresh_im):
    '''Finds parts of the object definitely associated with the individual image'''
    '''Useful for segmentation'''
    print('Removing Noise')
    kernel=np.ones((1,1),np.uint8)
    opening = cv2.morphologyEx(thresh_im,cv2.MORPH_OPEN,kernel, iterations=2)

    print('Finding background')
    #sure background area
    sure_bg=cv2.dilate(opening,kernel,iterations=1)
    print('Finding foreground')
    #finding sure foreground area
    dist_transform=cv2.distanceTransform(opening,cv2.cv.CV_DIST_L2,0)
    ret, sure_fg=cv2.threshold(dist_transform,0.99*dist_transform.max(),255,0)

    print('Obtaining unknown region...')
    #finding unknow region
    sure_fg = np.uint8(sure_fg)
    unknown=cv2.subtract(sure_bg,sure_fg)

    #Marker labelling
    print('Labelling Markers...')
    ret, markers = cv2.cv.ConnectedComponents(sure_fg)
    #Add one to all labels so that sure background is not 0 but 1
    markers=markers+1

    #Mark the unknown regions with 0
    markers[unknown==255] = 0

    markers=cv2.watershed(thresh_im,markers)
    thresh_im[markers == -1] = [255,0,0]
    return(thresh_im)

def Edges(img,numberoferosions):
    '''Find the edge of an object'''
    print('Finding outlines...')
    eroded=Erode(img,2)
    edges=img ^ eroded
    return(edges)

def skeleton_endpoints(skel):
    '''Find the endpoints of your skeleton'''
    # make out input nice, possibly necessary
    skel = skel.copy()
    skel[skel!=0]=1
    skel=np.uint8(skel)

    #apply the conversion
    kernel = np.uint8([[1,1,1],[1,10,1],[1,1,1]])
    src_depth= -1
    filtered = cv2.filter2D(skel,src_depth,kernel)

    #now look through to find the value of 11
    #this returns a mask of the endpoints,
    #but if you just want the coordinates you could simply
    #return np.where(filtered==11)
    out = np.zeros_like(skel)
    out[np.where(filtered==11)]=1
    return np.where(filtered==11)

def Fill(Image):
    '''
    Fills in whole in connected reigons in Image.
    '''
    Filled = ndi.binary_fill_holes(Image)
    return(Filled)

def ConstructOverlay(Image1,Image2):
    '''
    Takes 2 images and overlays them for disply.
    '''
    p2, p98 = np.percentile(Image1, (0, 100))
    stretched_Image = exposure.rescale_intensity(Image1, in_range=(p2, p98))
    zeros = np.zeros((np.size(Image1,0),np.size(Image1,0)), dtype = np.uint16)
    overlay = np.dstack((Image1*Image2,Image2,zeros))
    return overlay

def Save(Image,pathname):
    '''
    Saves image to pathname as png.
    '''
    misc.imsave(pathname, Image)


def Compare(ImageArray,ColorBarArray=None, TitleArray=None,
        commonScaleBar=True,show=True):
    '''
    Places images side by side for comparsion.
    '''
    if TitleArray == None:
        TitleArray = ["A","B","C","D","E","F","G","H","I","J","K","L"]
    if ColorBarArray == None:
        ColorBarArray = range(1,len(ImageArray)+1)
    dimensionsArray = [(1,1),(1,2),(1,3),(2,2),(2,3),(2,3),(3,3),(3,3),(3,3),(4,3),(4,3),(4,3)]
    rows, columns = dimensionsArray[len(ImageArray)-1]
    i=0
    fig , ax = plt.subplots(nrows=rows,ncols=columns,figsize=(20,10))
    if len(ImageArray)<4:
        ax = np.vstack((ax,ax))
    for y in range(rows):
        for x in range(columns):
            if(i > len(ImageArray)-1):
                break
            if commonScaleBar:
                im4 = ax[y][x].imshow(ImageArray[i], cmap= "jet",interpolation='None', vmin=np.min(ImageArray),vmax=np.max(ImageArray))
            else:
                im4 = ax[y][x].imshow(ImageArray[i], cmap= "jet",interpolation='None')
            #ax[y][x].axis('off')
            ax[y][x].set_title(TitleArray[i])
            if i+1 in ColorBarArray:
                divider4 = make_axes_locatable(ax[y][x])
                ax[y][x] = divider4.append_axes("right", size="5%", pad=0.05)
                cbar4 = plt.colorbar(im4, cax=ax[y][x])
            #ax[y][x].xaxis.set_visible(False)
            i += 1
    plt.tight_layout()
    if show:
        plt.show()
    return ax

def Show():
    '''
    Shows image at run time.
    '''
    plt.show()

def SavePlot(filename):
    '''
    Saves plot to pathname as png.
    '''
    plt.savefig(filename + ".png")

def SaveCellToFile(cellImage,binaryImage,parentFolder,fileName,path):
    '''
    Saves cell image to pickle file
    '''
    dictionary = {"ParentFolder":parentFolder,"FileName":fileName,
            "RawImage":cellImage, "BinaryMask":binaryImage}
    f = open(path,'a')
    pickle.dump(dictionary, f)
    f.close()

def LoadCellFromFile(path):
    f = open(path,'r')
    dictionary = pickle.load(f)
    return dictionary

def FolderCompare(FolderName):
    '''
    Compares all images in a folder on screen.
    '''
    filenames = os.listdir(FolderName)
    Images = []
    for file in filenames:
        Images.append(Open(os.path.join(FolderName,file)))
    Compare(Images)
    Show()

def AniShow(images,delay=1,cmap='gray',title=""):
    plt.ion()
    for image in images:
        plt.clf()
        plt.title(title)
        plt.imshow(image,interpolation='none',cmap=cmap)
        plt.colorbar()
        plt.pause(delay)
    plt.close()
    plt.ioff()
