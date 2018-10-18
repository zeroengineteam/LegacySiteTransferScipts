
import os
import sys


def ProcessFile(fileObj):
    result = ""
    line = fileObj.readline()
    
    #skip to related materials section
    while not("=Related Material" in line or "= Related Material" in line or "=Manual" in line or "==Manual" in line or "= Manual" in line or "== Manual" in line or line == ""):
        result += line
        line = fileObj.readline()


    
    while not(line == ""):
        if not(line[0] == "=" or line[0] == " " or line[0] == "\n" or line[0] == "-"):
          line = "- " + line

        result += line

        line = fileObj.readline()

    return result






# Set the directory you want to start from
rootDir = '.'
translatedDir = "I:\\github\\translated_files"
for dirName, subdirList, fileList in os.walk(rootDir):
    #print('Found directory: %s' % dirName)
    for fname in fileList:
        filePath = dirName + "\\" + fname
        fileCopyPath = dirName + "\\" + fname
        if(".remarkup" in filePath):
            print("processing: " + filePath)
            fileObj = open(filePath, "r")
            result = ProcessFile(fileObj)
            result += " \n "
            fileObj.close()
            fileObj = open(fileCopyPath, "w")
            fileObj.write(result)
            fileObj.close()
