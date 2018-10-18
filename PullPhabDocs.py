
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

def GetPhrictionDoc(cursorAfter):
    #query key for zero engine tagged tasks
    queryKey = ""
    constraints = {}
    constraints["statuses"] = ["active"]
    constraints["ancestorPaths"] = ["zero_engine_documentation/"]
    attachments = {}
    attachments["content"] = True
    attachments["subscribers"] = True
    attachments["projects"] = True
    response = None

    dir_path = os.path.dirname(os.path.realpath(__file__))
    print(dir_path)

    try:
        print("searching at " + str(cursorAfter) )
        response = phab.phriction.document.search(queryKey=queryKey, constraints=constraints, attachments=attachments, after=cursorAfter);
    except APIError:
        print("APIError")
        print(APIError.message)
    else:
        print("Search Response: Cursor at " + str(response.cursor))
        data = response.data
        
        for page in data:
            phid = page["phid"]
            
            fields = page["fields"]
            path = fields["path"]
            print(path)
            status = fields["status"]

            attachments = page["attachments"]
            subscribers = attachments["subscribers"]
            projects = attachments["projects"]
            content = attachments["content"]

            splitPath = path.split("/")
            curPath = dir_path + "\\"
            fileName = splitPath[len(splitPath)-2]
            print(fileName)
            for directory in splitPath:
                if(directory == fileName):
                    break

                curPath += directory + "\\"
                if not(os.path.isdir(curPath)):
                    print(curPath + " does not exist: creating")
                    os.mkdir(curPath)

            title = content["title"]
            body = content["content"]["raw"]
            filePath = curPath + fileName
            with open(filePath + ".remarkup", "w") as f:
                f.write(body)
                f.close()




        if(len(response.data) >= 100):
            GetPhrictionDoc(response.cursor['after'])

GetPhrictionDoc(0)



