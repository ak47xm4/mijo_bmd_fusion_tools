"""""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """'
ReloadLoaders
-------------
Version: v1.03
Last update: 24 Sep 2019

Description:The ReloadLoaders script will refresh all or selected Loader nodes in your comp
            by rereading the "clip" filename attribute so it also updates the footage
            for the full duration of the sequence.

Installation: copy AlbertoGZ/ReloadLoaders folder in your Fusion:/Scripts/Comp/

Author: AlbertoGZ
Email: albertogzgz@gmail.com
Website: albertogz.com

""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """"""

import os 
import re

comp.StartUndo('version_up')

allLoaders = comp.GetToolList(False, "Loader").values()
selLoaders = comp.GetToolList(True, "Loader").values()

# Check if selection and builds list with Loaders in,
# otherwise list inlcude all Loaders
if selLoaders:
    toollist = selLoaders
else:
    toollist = allLoaders

# add comp lock to remove prompt window
comp.Lock()
# Evaluate Loaders in list

# mijo fix bug
currentTime = comp.CurrentTime
comp.CurrentTime = comp.GetAttrs('COMPN_GlobalStart')

for tool in toollist:
    loaderPath = tool.GetAttrs("TOOLST_Clip_Name")
    loaderName = tool.GetAttrs("TOOLS_Name")
    loaderPathClean = loaderPath[1]
    durationOld = tool.GetAttrs("TOOLIT_Clip_Length")
    durationOldClean = durationOld[1]
    
    # mijo add version switch
    post_version_path = loaderPathClean
    # something like \v001\
    p = re.compile('\\\\v\d\d\d\\\\') 
    p_search_1 = p.search(post_version_path)
    
    #print(p_search_1[0])
    p_search_1_version_num = int(p_search_1[0][2:-1])
    
    p_search_1_version_num = min(max(p_search_1_version_num,0),999)
    
    #print(p_search_1_version_num)
    for i in range(999,p_search_1_version_num,-1):
        p_search_1_version_num = i
        p_search_1_version_num_Str = '{:03d}'.format(p_search_1_version_num)
        #print(p_search_1_version_num_Str)
        
        p_search_1_version_num_Str = 'v'+p_search_1_version_num_Str
        
        #print(p_search_1_version_num_Str)
        
        to_replace = '\\\\'+p_search_1_version_num_Str+'\\\\'
        
        #post_version_path = re.sub(r'\\\\v\d\d\d\\\\',to_replace,post_version_path)
        post_version_path = re.sub('\\\\v\d\d\d\\\\',to_replace,post_version_path)
        
        remap_path = comp.MapPath(post_version_path)
        

        isExist = os.path.exists(remap_path)
        #print(isExist)
        if isExist :
            print(str(p_search_1[0])+'____'+to_replace)
            print(post_version_path)
            break
    
    loaderPathClean = post_version_path
    
    # Rename the clipname to force reload duration
    tool.Clip = loaderPathClean + ""
    tool.Clip = loaderPathClean
    durationNew = tool.GetAttrs("TOOLIT_Clip_Length")
    durationNewClean = durationNew[1]

    # Disable/enable to reload clip cache
    tool.SetAttrs({"TOOLB_PassThrough": True})
    tool.SetAttrs({"TOOLB_PassThrough": False})

    # Outputs
    print(loaderName + " has been reloaded.")
    #print(" + current filename: " + tool.Clip[0])
    #print(" + old duration: " + str(durationOldClean) + " frames")
    #print(" + new duration: " + str(durationNewClean) + " frames")
    #print("")
    
    ## mijo frame num abs
    filePath = loaderPath[1].split('.')
    try:
        filePathFrameStr = filePath[-2]
        filePathFrame = int(filePathFrameStr)
    except ValueError :
        filePathFrame = 0
    
    
    
    tool.GlobalOut[fusion.TIME_UNDEFINED] = filePathFrame+durationNewClean-1
    tool.GlobalIn[fusion.TIME_UNDEFINED] = filePathFrame
    
    tool.ClipTimeStart[fusion.TIME_UNDEFINED] = 0
    tool.ClipTimeEnd[fusion.TIME_UNDEFINED] = durationNewClean
    
    tool.GlobalOut[fusion.TIME_UNDEFINED] = filePathFrame+durationNewClean-1

comp.CurrentTime = currentTime

comp.Unlock()


comp.EndUndo(True)