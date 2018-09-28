# -*- coding: utf-8 -*-

# Uses Python 2.7

import os
import sys
import requests

#imports for phabricator api client
import re
import pycurl
import base64
import string
import simplejson as json
import ssl
import requests
from socket import *

from phabricator import Phabricator
from phabricator import APIError


phab = Phabricator()
phab.update_interfaces()
phab.timeout = 100.0

print("WHO AM I?")
print("=========")
me = phab.user.whoami()
print(me)

phab_tasks_fileName = "phab_tasks.json"
file_repo_url = "https://github.com/zeroengineteam/ZeroFiles/task_files/"

fileIDToFileExt = {}

def GetPhabTask(outfile, cursorAfter):
    #query key for open zero engine tagged tasks on old dev.zeroengine.io
    queryKey = "xdRHwRHZaSkp"
    constraints = {}
    constraints["statuses"] = ["open"]
    attachments = {}
    attachments["subscribers"] = True
    attachments["projects"] = True
    response = None
    
    tasks = []

    #Attempt to query all tasks tagged with zero engine
    try:
        print("searching at " + str(cursorAfter) )
        response = phab.maniphest.search(queryKey=queryKey, constraints=constraints, attachments=attachments, after=cursorAfter);
    except APIError as e:
        print("APIError")
        print(str(e))
    else:
        print("Search Response: Cursor at " + str(response.cursor))
        data = response.data
        
        #Append tasks from this reponse to the list
        for task in data:
            tasks.append(task)

        #If the the cursor is still above 100 it means that we more tasks to request
        if(len(response.data) >= 100):
            result = GetPhabTask(outFile, response.cursor['after'])
            for task in result:
                tasks.append(task)

    return tasks

#Trim the f off the file ID
def TrimFileID(rawFileRef):
    result = re.search("F\d*", rawFileRef)
    trimmedID = result.group(0)
    return trimmedID

#Returns list of file IDs found in the serialized task json file
def GetFileIDs(infile):
    fileIDRegEx = "(\{)(\s*?)(F\d.*?)(\s*?)(,\s*?size=full\s*?|\s*?size=full\s*?|)(\})"
    taskData = infile.read();
    fileIDMatches = re.findall(fileIDRegEx, taskData)
    fileIDs = []

    for match in fileIDMatches:
        trimmedID = match[2]
        print(trimmedID)
        fileIDs.append(trimmedID)

    return fileIDs

def GetNewFileURL(fileID):
  return file_repo_url + fileID

#Takes the file ID list returned by GetFileIDs and downloads all files from phabricator in a folder structure reflecting task IDs
def DownloadFilesFromPhabricator(fileIDs):
    if not(len(fileIDs) > 0):
      return {}

    constraints = {}
    currentID = fileIDs[0]
    constraints["ids"] = [int(currentID[1:])];
    response = None

    idsToFileNames = {}

    try:
        print("Searching for meta data for file with ID: " + str(constraints["ids"])) 
        response = phab.file.search(constraints=constraints)
    except APIError:
        print("APIError in DownloadFilesFromPhabricator CurrentID: " + str(constraints["ids"]))
        print(APIError.message)
        return {}
    else:
      data = response.data
      for fileData in data:
          fields = fileData["fields"]
          name = fields["name"]
          dataURI = fields["dataURI"]
          GetAndWriteFileData(name, currentID, dataURI)
          idsToFileNames[name] = currentID
          fileIDToFileExt[currentID] = name[-4:]

      results = DownloadFilesFromPhabricator(fileIDs[1:])
      return {**idsToFileNames, **results}

#Writes streamed file data to disk, data may come in multiple responses
def GetAndWriteFileData(fileName, currentID, dataURL):
    print("Request " + fileName)
    path = "./ZeroFiles/task_files/"

    fullPath = path + str(currentID) + fileName[-4:]
    if(os.path.exists(fullPath)):
        print("    File already exists.")
        return

    with open(fullPath, 'wb') as handle:
        response = requests.get(dataURL, stream=True)
        
        if not response.ok:
            print(response)
    
        for block in response.iter_content(1024):
            if not block:
                break
    
            handle.write(block)


#If the seriailized JSON file of tasks already exists delete it
if(os.path.exists(phab_tasks_fileName)):
    os.remove(phab_tasks_fileName)

#Query and seriliaze all phabricator tasks
outFile = open(phab_tasks_fileName, "a")
tasks = GetPhabTask(outFile, 0)
taskObj = { "data" : tasks}
tasksJSON = json.dumps(taskObj)
outFile.write(tasksJSON)
outFile.close()

#Record and serialize fileIDs out of the task file
taskFile = open(phab_tasks_fileName, "r")
fileIDs = GetFileIDs(taskFile)
taskFile.close()

#Download all files found in tasks
idsToFileNames = DownloadFilesFromPhabricator(fileIDs)

#Serialize File extensions mapped to fileIDs for when we are replacing by ID
fileIDFile = open("fileIDToFileExt.json", "w")
fileIDFile.write(json.dumps(fileIDToFileExt))
fileIDFile.close()