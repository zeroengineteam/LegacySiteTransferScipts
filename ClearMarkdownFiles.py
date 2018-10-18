
import os
import sys
# Set the directory you want to start from
rootDir = '.'
translatedDir = "I:\\github\\translated_files"
for dirName, subdirList, fileList in os.walk(rootDir):
    #print('Found directory: %s' % dirName)
    for fname in fileList:
        filePath = dirName + "\\" + fname
        if(".markdown" in filePath):
            os.remove(filePath)
            continue

        if("copy" in filePath):
            os.remove(filePath)
            continue
