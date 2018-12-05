#!/usr/bin/env python

#
# Author: Eduardo X. Miqueles
#         2017, March
#         LNLS/CNPEM

import sys
import glob
import os
import getopt
import stat

from os import listdir
from os.path import isfile, join
import re

import matplotlib.pyplot as plt
import h5py
import numpy
import subprocess
from subprocess import Popen, PIPE, STDOUT

#################################################
#
# mkdir -p for a given path
#
# TODO: migrate to subprocess?

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

##################################################
#
#
# Extract tomo informations from setup.txt
#
#

def isGroupReadable( filepath ):
    """
    Check if a group is readable
    """
    st = os.stat( filepath )
    return bool(st.st_mode & stat.S_IRGRP)


def convert_bytes(num):
    """
    Convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

        
def tomo_file_size(file_path):
    """
    Return the file size
    """
    if os.path.isfile(file_path):
        file_info = os.stat(file_path)
        filesize =  convert_bytes(file_info.st_size)

    if filesize[4:6]=="GB":
        value = float(filesize[0:3])
    else: #filesize[4:6]=="MB":
        value = float(filesize[0:3])/1024.0
    
    return value


def tomo_status( path ):
    """
    Check tomography status

    If   "#Finished Time"  is written within sample.txt => true : return 1
    Else                                                   false: return 0                                               
    """

    Path = path

    path_sample = os.path.join(Path, 'sample.txt')
    path_h5 = os.path.join(Path, 'tomo.h5' )

    exist_sample_file = os.path.exists(  path_sample )

    if exist_sample_file:
    
        #
        #http://stackoverflow.com/questions/1861836/checking-file-permissions-in-linux-with-python
        #
        #check permission from sample.txt

        permission = isGroupReadable(  path_sample )
        
        permission_h5 = isGroupReadable(  path_h5 )

        if permission: #& permission_h5:

            cmd='grep "#Finish Time" ' +  path + '/sample.txt > /dev/null; echo $?'  
            
            p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
            
            try:
                output = int(p.stdout.read())
            except ValueError:
                return 0
        
            return 1 - output
            
        else:
            return 0
    else:
        return 0

#

def tomo_exposure_time( ):
    """
    Get exposure time from sample.txt (in milliseconds)
    """
    
    cmd='grep "#Exposure Time" ' +  "tail.txt | awk 'END{print  $4}'"  
   
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)

    time = p.stdout.read()

    #print time

    try:
        int(time)
    except ValueError:
        time = -1
    
    return int(time)

def tomo_detector_position( ):
    """
    Get detector position from sample.txt (in millimeters)
    """
    
    cmd='grep "#Detector Position" ' +  ' tail.txt > /dev/null; echo $?'  
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    check = int( p.stdout.read() )
    
    if( check ):
        distance = 666
    else:
        cmd='grep "#Detector Position" ' +  "tail.txt | awk 'END{print  $4}'"  
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        distance = p.stdout.read()
    
    return float(distance)


def tomo_number_of_projections( ):
    """
    Get number of projections from sample.txt
    """
    
    cmd='grep "#Number of Projections" ' +  "tail.txt | awk 'END{print  $5}'"  
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    nangles = p.stdout.read()
    
    return int(nangles)

    
def tomo_get_filters( ):
    """
    Get number of filters from sample.txt
    """
    
    check= [0,0,0,0]

    for k in range(4):
        strg = '"#Filter'+str(k)+'" '
        cmd='grep '+strg + 'tail.txt | wc -l' 
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        check[k] = int(p.stdout.read())

    
    if sum(check)==0:
        mono = 1
    else:
        mono = 0
        
    return sum(check), check, mono


def tomo_get_time( ):
    """
    Get absolute time + year of tomo from sample.txt
    """
    
    strg = '"#Start Time"'
    cmd='grep '+ strg + " tail.txt | awk '{print $4}'"  
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    year = str(p.stdout.read())
    year = int(year[0:4])

    strg = '"#Start Time"'
    cmd='grep '+ strg + " tail.txt | awk '{print $5}'"  
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    hour = str(p.stdout.read())
    hora = float(hour[0:2])
    minutos = float(hour[3:5])
        
    return year, hora+minutos/100


def tomo_get_angle_range( ):
    """
    Get angle range from sample.txt
    """
    
    strg = '"#Angle Range"'
    cmd='grep '+ strg + " tail.txt | awk '{print $4}'"  
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    angle = float(p.stdout.read())

    return angle


def tomo_get_sinogram( path, k ):

    name_buff = "tomo"
    
    dir_buff = path 
    dir_files = [ f for f in listdir(dir_buff) if isfile(join(dir_buff, f)) ]
    prog_files = [(name_buff + '.h5'), (name_buff + '_dark_before.h5'), (name_buff + '_dark_before.h5'), (name_buff + '_flat_after.h5'), (name_buff + '_flat_before.h5')]
    
    #
    # extracting sino from HDF5 file
    #
    
    name_tomo = os.path.join(dir_buff, prog_files[0])
    f_tomo = h5py.File(name_tomo, "r")
    dset_tomo = f_tomo["images"]
    
    name_flat_before = os.path.join(dir_buff, prog_files[3])
    f_flat_before = h5py.File(name_flat_before, "r")
    dset_flat_before = f_flat_before["flats"]
    
    name_dark_before = os.path.join(dir_buff, prog_files[1])
    f_dark_before = h5py.File(name_dark_before, "r")
    dset_dark_before = f_dark_before["darks"]
    
    name_flat_after = os.path.join(dir_buff, prog_files[4])
    f_flat_after = h5py.File(name_flat_after, "r")
    dset_flat_after = f_flat_after["flats"]
    
    name_dark_after = os.path.join(dir_buff, prog_files[2])
    f_dark_after = h5py.File(name_dark_after, "r")
    dset_dark_after = f_dark_after["darks"]
    
    #
    #
    
    frame = dset_tomo[:, k, :].astype(numpy.double)	
   
    dark_before = dset_dark_before[0, k, :].astype(numpy.double)
    dark_after = dset_dark_after[0, k, :].astype(numpy.double)
    
    n_angles = frame.shape[0]
    n_rays = frame.shape[1]
    
    flat_before = dset_flat_before[0, k, :].astype(numpy.double)
    flat_after = dset_flat_after[0, k, :].astype(numpy.double)
    
    # -----------------------------------------
    # creating flat and dark correction vectors
    
    sino_flat = numpy.zeros([n_angles, n_rays])
    
    for idx in range(n_angles):
        interp = flat_before + (flat_after-flat_before) * idx /(float(n_angles-1))
        sino_flat[idx,:] = interp[:]
    
    i  = numpy.ones((n_angles,1)) 
    sino_dark = numpy.kron(i, dark_before) 
    
    corr_flat = sino_flat - sino_dark
    corr_flat_zeros = numpy.abs(corr_flat)< 1e-5	
    corr_flat[corr_flat_zeros] = 1
    
    corr_dark = frame - sino_dark
    
    buff_img = (corr_dark)/corr_flat	
    buff_zeros = numpy.abs(buff_img)< 1e-5	
    
    buff_img[buff_zeros] = 1
    
    counts_ = buff_img
    flat_ = sino_flat 
    
    sino = -numpy.log(buff_img)	
    
    pos = numpy.where( numpy.isnan(sino) == True )
    sino[pos] = 0    

    sino = numpy.transpose(sino)
    sino_flat = numpy.transpose(sino_flat)
    sino_dark = numpy.transpose(sino_dark)

    if hasattr(f_tomo, 'close'):
        f_tomo.close()

    if hasattr(f_flat_before, 'close'):
        f_flat_before.close()

    if hasattr(f_flat_after, 'close'):
        f_flat_after.close()

    if hasattr(f_dark_after, 'close'):
        f_dark_after.close()

    if hasattr(f_dark_before, 'close'):
        f_dark_before.close()

    return sino, sino_flat, sino_dark


#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@
#@@@@@  main code ( )
#@@@@@

r = ''

def usage():
    print("\nIMX Statistics\n\n Example: \timx_stats -r /storage/to/search/")

options, remainder = getopt.getopt(sys.argv[1:], 'hr:', ['r='])

for opt, arg in options:
    if opt == "-h":
        usage()
        sys.exit()
    elif opt in ('-r', '--root'):
        r = str(arg)
    else:
        sys.exit()

rootdir = r

print('Searching IMX statistics: ', rootdir)

###############################################
#
# Searching tomo.h5 within folders from storage
#

count   = 0
sliceno = 1200

FP = open('/ddn/IMX/IMXTemp/IMXStatistics/lixo.dat','w')

for root, subFolders, files in os.walk(rootdir):
    
    if 'tomo.h5' in files:
    
        if tomo_status ( root ):
            
            tomo_file = os.path.join(root, 'tomo.h5')
            
            print tomo_file
            
            #sinogram, sinogram_flat, sinogram_dark = tomo_get_sinogram( root, sliceno ) 
            
            #plt.plot(numpy.mean(sinogram_flat, 0))
            #plt.show()
            
            #fp = open( rootdir + '/IMXStatistics/sinograms/sinogram_'+str(count)+'.b','w')
            #sinogram.astype(numpy.double).tofile(fp)
            #fp.close()
            
            #fp = open( rootdir + '/IMXStatistics/sinograms/sinogram_flat_'+str(count)+'.b','w')
            #sinogram_flat.astype(numpy.double).tofile(fp)
            #fp.close()
            #
            #fp = open( rootdir + '/IMXStatistics/sinograms/sinogram_dark'+str(count)+'.b','w')
            #sinogram_dark.astype(numpy.double).tofile(fp)
            #fp.close()
            
            #plt.imshow(sinogram_flat)
            #plt.show()

            #print root, subFolders, files

            #################################################################
            ### get tail from sample.txt (consistency information: last tomo)

            cmd='grep -in "#Angle Range" ' +  root + "/sample.txt | awk -F: 'END{print $1}'"
            p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
            linenumber = int(p.stdout.read())
            
            cmd='tail --lines=+' + str(linenumber-1)+' ' +  root + "/sample.txt > tail.txt"
            subprocess.call(cmd, shell=True)
            #################################################################
            
            filesize = tomo_file_size( tomo_file )
            
            exptime = tomo_exposure_time()
    
            distance = tomo_detector_position()
            
            nangles = tomo_number_of_projections()
            
            nfilters, filters, mono = tomo_get_filters()

            year, hour = tomo_get_time()

            angle = tomo_get_angle_range()

            print >> FP, year,'\t', filesize,'\t',nangles,'\t',exptime,'\t',distance,'\t',nfilters,'\t',filters[0],filters[1],filters[2],filters[3],'\t',hour,'\t',mono,'\t',angle,'\t',count,'\t', root 
            #print count, year, root
            
            ###############################
            ## remove file tail.txt
            cmd='rm tail.txt'  
            subprocess.call(cmd, shell=True)
            ################################

            count += 1

FP.close()
