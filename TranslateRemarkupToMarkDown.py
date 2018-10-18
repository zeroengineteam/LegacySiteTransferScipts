
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

file_repo_url = "https://media.githubusercontent.com/media/zeroengineteam/ZeroFiles/master/doc_files/"
doc_repo_url = "https://github.com/zeroengineteam/ZeroDocs/blob/master/"

#Takes the file ID list returned by GetFileIDs and downloads all files from phabricator in a folder structure reflecting task IDs
def DownloadFileFromPhabricator(fileID):
    constraints = {}
    constraints["ids"] = [int(fileID)];
    response = None

    try:
        #print("Searching for data for file with ID: " + str(constraints["ids"])) 
        response = phab.file.search(constraints=constraints)
    except APIError as e:
        print("APIError on file download: ")
        print("  " + str(e))
        #print("APIError in DownloadFilesFromPhabricator CurrentID: " + str(constraints["ids"]))
        #print(APIError.message)
        return {}
    else:
        data = response.data
        for fileData in data:
            fields = fileData["fields"]
            name = fields["name"]
            dataURI = fields["dataURI"]

            #some images were some how uploaded and used without a file extension.
            #I am assuming these are pngs as there is no way to tell
            if not("." in name):
                name += ".png"

            fileExt = name[-4:]
            GetAndWriteFileData(name, fileID, dataURI, fileExt)

            return name, fileID, dataURI, fileExt

#Downloads text contents of a paste and emplaces it where there was a reference to the paste
def GetPaste(pasteID):
    print("    Get Paste: " + str(pasteID))
    #query key for zero engine tagged tasks
    queryKey = ""
    constraints = {}
    constraints["ids"] = [int(pasteID)]
    attachments = {}
    attachments["content"] = True
    response = None

    dir_path = os.path.dirname(os.path.realpath(__file__))
    #print(dir_path)

    result = ""
    try:
        response = phab.paste.search(constraints=constraints, attachments=attachments);
    except APIError as e:
        print("APIError")
        print(e)
    else:
        #print("Search Response: Cursor at " + str(response.cursor))
        data = response.data
        #print(data)
        for page in data:
            attachments = page["attachments"]
            content = attachments["content"]["content"]
            result += content

    return result


#Writes streamed file data to disk, data may come in multiple responses
def GetAndWriteFileData(fileName, currentID, dataURL, ext):
    path = "I:\\github\\ZeroFiles\\doc_files\\"
    #if the file already exists don't redownload it
    fullPath = path + str(currentID) + ext
    if(os.path.exists(fullPath)):
        return

    #print("Writing File: " + fileName + " ID: " + currentID)
    with open(fullPath, 'wb') as handle:
        response = requests.get(dataURL, stream=True)
        
        if not response.ok:
            print(response)
    
        for block in response.iter_content(1024):
            if not block:
                break
    
            handle.write(block)


#contains some sub functions that are utiliies for translating links
def TranslateURLLinks(content, filePath):
    #define the match callback functions inside so the can have access to the function params
    #substitution function for inserting markdown file extension in urls with #fragments
    def EmplaceMarkdownExtWithFragment(matchObj):
        fragment = matchObj.group(2)
        return ".markdown" + "#" + fragment

    #substitution function for inserting markdown file extension in urls withithout #fragments
    def EmplaceMarkdownExt(matchObj):
        return matchObj.group(0) + ".markdown"

    def AppendMarkdownExt(url):
        #print("Appending to: " + url)
        url = url.replace("\\", "/")
        url = url.strip()

        if(url[len(url)-1] == "/"):
            url = url[:-1]


        result = ""
        #substitution for inserting markdown file extension in urls with #fragments
        if("#" in url):
            result = re.sub("(\/?\#)(\S*)", EmplaceMarkdownExtWithFragment, url)

        #substitution for inserting markdown file extension in urls with #fragments
        else:
            if("/" in url):
                result = re.sub("\/(?:.(?!\/))+$", EmplaceMarkdownExt, url)
            else:
                result = url + ".markdown"

        return result

    #returns the final directory or file in the given path
    def GetFileOrFinalDir(path):
        #strip any trailing / so the while loops always runs, I wish this could be a do while
        #print("GetFileOrFinalDir: Path: " + path)
        path = path.replace("\\", "/")
        path = path.strip()
        index = len(path)-1
        if(path[index] == "/"):
            path = path[:-1]
            index = len(path)-1

        lastElement = ""
        while(index >= 0):
            char = path[index]
            if(char == "/"):
                break
            else:
                lastElement += char
            
            index -= 1

        result = lastElement[::-1]
        #print("GetFileOrFinalDir: result: " + result)
        return result


    #removes the trailing directory from the given path
    def StripTopDirectory(path):
        newPath = path.replace("\\", "/")
        #print("          Stripping Path: " + newPath)

        #if passed a directory path strip initial \ so the while loop still runs
        if(newPath[len(newPath)-1] == "/"):
            newPath = newPath[:-1]

        while (len(newPath) > 0 and not newPath[len(newPath)-1] == "/"):
            newPath = newPath[:-1]

        if(newPath[len(newPath)-1] == "/"):
            newPath = newPath[:-1]

        #print("          Stripped Path: " + newPath)
        return newPath

    #URL LINKS
    def TranslateIconURLLink(matchObj):
        #print("      TranslateIconURLLink: ")
        slug = matchObj.group(3)
        slug = slug.replace("zero_engine_documentation/", "")
        slug = slug.replace("\\", "/")
        mask = matchObj.group(6)

        url = doc_repo_url + slug
        if(mask.strip() == ""):
            mask = GetFileOrFinalDir(slug)
            #print("replacing mask with: " + mask)
        #else:
        #    print("not replacing mask: " + mask)
    
        url = AppendMarkdownExt(url)
        maskedURL = "[" + mask + "](" + url + ")"
        #print("Gen URL for doc: " + str(mask) + " URL: " + url)
        maskedURL = maskedURL.replace("\\", "/")
        maskedURL = maskedURL.replace("zero_engine_documentation/", "")
        return maskedURL
    
    def TranslateExternalLink(matchObj):
        print("      TranslateExternalLink")
        externalURL = matchObj.group(3)
        mask = matchObj.group(6)

        if(mask.strip() == ""):
            mask = GetFileOrFinalDir(slug)
            print("replacing mask with: " + mask)
    
        maskedURL = "[" + mask + "](" + externalURL + ")"
        maskedURL = maskedURL.replace("\\", "/")
        return maskedURL
    
    #Github doesn't handle relative path linking
    def TranslateRelativeInternalLink(matchObj):
        #print("      TranslateRelativeInternalLink: ")
        relativePath = matchObj.group(4)
        relativePath = relativePath.replace("\\", "/")
        subSlug = matchObj.group(5)
        subSlug = subSlug.replace("\\", "/")
        #print("        RelativePath: " + relativePath)
        #print("        Slug: " + subSlug)
        #print("        path: " + filePath)
        mask = matchObj.group(8)
        url = ""

        #remove filename from subSlug
        absolutePath = filePath
        absolutePath = absolutePath.replace("\\", "/")
        #absolutePath = StripTopDirectory(filePath)
        #print("        absolutePath: " + absolutePath)

        #traverse up from the file "we are in"
        relativeDirs = re.findall("\.\.\/", relativePath)
        for directory in relativeDirs:
            absolutePath = StripTopDirectory(absolutePath)
        
        absolutePath += "/"
        #print("        absolutePath after strip: " + absolutePath)

        if not(subSlug == ""):
            #print("append to slug: " + subSlug)
            subSlug = AppendMarkdownExt(subSlug)
            url = doc_repo_url + absolutePath[2:] + subSlug
        else:
            #print("append to path: " + absolutePath)
            absolutePath = AppendMarkdownExt(absolutePath);
            url = doc_repo_url + absolutePath[2:]

        if(mask.strip() == ""):
            mask = GetFileOrFinalDir(url)

        maskedURL = "[" + mask + "](" + url + ")"
        #print("        Resulting URL: " + maskedURL)

        maskedURL = maskedURL.replace("\\", "/")
        maskedURL = maskedURL.replace("zero_engine_documentation/", "")
        return maskedURL

    #link mask is captured in group 5 if there is one otherwise it is empty, the page slug is in capture group 3
    remarkupIconLinkRegex = "(\{icon.*?\})?\[\[(\s*)([a-zA-Z0-9\_\/\#\- ]*)(\s*?)\|?(\s*?)?([a-zA-Z0-9\_\- \(\)\.\&\(\)]*)?(\s*?)?(\]\])(\{icon.*?\})?"
    externalLinkRegex = "(\{icon.*?\})?\[\[(\s*)?(https?\:\/\/[^|\]]*)(\s*)?\|?(\s*)?([a-zA-Z\.\/\_\-0-9 \&\(\)]*)?(\s*)?\]\]"
    relativeInternalLinkRegex = "(\{icon [a-zA-Z0-9\-\_]+\})?\[\[((\s*)?(\.?\.\/)+)([a-zA-Z\.\/\_\-0-9\#]*)(\s*)?\|?(\s*)?([a-zA-Z\.\/\_\-0-9 \&\(\)]*)?\]\](\{icon [a-zA-Z0-9\-\_]+\})?"
    newContent = re.sub(remarkupIconLinkRegex, TranslateIconURLLink, content)
    newContent = re.sub(externalLinkRegex, TranslateExternalLink, newContent)
    newContent = re.sub(relativeInternalLinkRegex, TranslateRelativeInternalLink, newContent)
    return newContent

def TranslateKeyDirectives(content):
    def TranslateKeyDirective(matchObj):
        result = ""
        keyString = matchObj.group(2)
        keyString = keyString.replace(" ", " + ")
        return "`" + keyString + "`"


    keyRegex = "(\{key )([^\}]*)\}"
    newContent = re.sub(keyRegex, TranslateKeyDirective, content)
    return newContent[:-1]

def TranslatePastes(content):
    def TranslatePasteDirective(matchObj):
        result = ""
        pasteID = matchObj.group(1)
        #print("PasteContent for Paste: " + pasteID)
        pasteContent = GetPaste(pasteID)
        #print("  " + pasteContent)
        return "```\n" + pasteContent + "\n```\n"

    pasteRegex = "\{P(\d*)([a-zA-Z0-9\=\, \-]*)\}"
    newContent = re.sub(pasteRegex, TranslatePasteDirective, content)
    return newContent



def TranslateHeaders(content):
    def TranslateMatchedHeaderToMarkdown(match):
        result = "\n "
        for char in match.group():
            if(char == "="):
                result += "#"
        
        result += " "
        return result

    def AppendNewlineToHeaders(matchObj):
        newlineHeaderSyntax = matchObj.group(1)
        header = matchObj.group(2)
        return "\n" + newlineHeaderSyntax + " " + header + "\n\n"

    headerRegex = "\n\=+"
    newContent = re.sub(headerRegex,TranslateMatchedHeaderToMarkdown, content)
    headerRegex = "^\=+"
    newContent = re.sub(headerRegex,TranslateMatchedHeaderToMarkdown, newContent)
    headerRegex = "(\n\#+)(.*)\n"
    newContent = re.sub(headerRegex,AppendNewlineToHeaders, newContent)
    return newContent

def TranslateNavs(content):
    def WholeNavCapture(wholeMatchObj):
        #print("  Whole NAV: " + str(wholeMatchObj))
        def TranslateNestedNav(nestedMatchObj):
            #print("    Internal NAV: " + str(nestedMatchObj))
            iconStr = nestedMatchObj.group(1)
            nameStr = nestedMatchObj.group(2)
            nestedResult = nameStr
            if(nestedMatchObj.group(3)):
                nestedResult += " > "
            return nestedResult

        nestedNavRegex = "icon\=([a-z\-]*), name\=([a-zA-Z \-]*)(\>\s*)?"
        wholeNavContent = wholeMatchObj.group(1)
        internalContent = re.sub(nestedNavRegex, TranslateNestedNav, wholeNavContent)
        return "`" + internalContent + "`"
    
    wholeNavRegex = "\{nav ([a-zA-Z\=\-\> , ]*)\}"
    newContent = re.sub(wholeNavRegex, WholeNavCapture, content)
    return newContent



#Returns corresponding github markdown formatted URL when passed a re module MatchObj for a remarkup formatted link
#This function is passed to re.replace in CreateIssue as the callback function for 
#  generating the replacement string on pattern match
def GenerateFileURL(matchObj):
    fileID = matchObj.group(3)
    
    name, currentID, dataURI, fileExt = DownloadFileFromPhabricator(fileID)

    url = "![" + name[:-4] + "](" + file_repo_url + fileID + fileExt + ")"

    #print("Gen File URL for FileID: " + str(fileID) + " URL: " + url)
    return url

def TranslateCaption(matchObj):
    caption = matchObj.group(1)
    #print("Caption: " + caption)
    return "\n\n*" + caption + "*\n"

def PrependNewLineOnFileRef(matchObj):
    #print("Prepend: " + matchObj.group(0))
    return "\n\n" + matchObj.group(0) + "\n"

def TranslateFileRefs(content):
    #print("Translate Refs: ")
    #print(content)

    fileIDRegEx = "(\{)(\s*?)F(\d+)(\s*?),?(\s*?size=full\s*?|\s*?size=full\s*?|.*?)(\})(\/\/[a-zA-Z \-\`]*\/\/)?"
    #fileIDRegEx = "(\{)(\s*?)F(\d+)(\s*?),?(\s*?size=full\s*?|\s*?size=full\s*?|.*?)(\})(\/\/.*\/\/)?$"
    newContent = re.sub(fileIDRegEx, GenerateFileURL, content)

    captionRegex = "(?<=\))\n?\/\/(.*)\/\/"
    newContent = re.sub(captionRegex, TranslateCaption, newContent)

    translatedFileRegex = "\n\!\[.*"
    newContent = re.sub(translatedFileRegex, PrependNewLineOnFileRef, newContent)

    return newContent

iconStrToText = {
    "wrench": "resource",
    "tag": "",
    "clone": "template",
    "square-o": "button",
    "check-square-o": "checkBox",
    "pencil-square-o": "",
    "list": "enum",
    "list-alt": "drop-down menu",
    "eyedroppper": "",
    "picture-o": "texture",
    "cog": "object",
    "cogs": "zero project",
    "crosshairs": "cogPath",
    "windows": "visual dtudio project",
    "file-code-o": "source code file",
    "window-restore": "window",
    "keyboard-o": "key",
    "mouse-pointer": "",
    "folder": "folder",
    "folder-open-o": "folder",
    "terminal": ""
}

def TranslateIcon(matchObj):
    iconStr = matchObj.group(3)
    text = matchObj.group(7)

    iconText = ""
    if(iconStr in iconStrToText.keys()):
        iconText = iconStrToText[iconStr]

    result = text + " " + iconText
    return result

def TranslateIcons(content):
    navIconRegex = "\{nav(\s*)?(icon\=)([a-zA-Z\-]*)(\s*)?\,?(\s*)?(name\=)?([a-zA-Z\-]*)\}"
    newContent = re.sub(navIconRegex, TranslateIcon, content)
    return newContent

def TranslateItalics(content):
    def TranslateItalic(matchObj):
        internalContent = matchObj.group(1)
        #print("Italics Content: " + internalContent)
        return "*" + internalContent + "*"

    italicsRegex = "(?<=\s)\/\/(.*)\/\/(?=\s)"
    newContent = re.sub(italicsRegex, TranslateItalic, content)
    return newContent

def PrependBulletsOnSingleLineLinks(content):
    def PrependLinkbullets(matchObj):
        matchContent = matchObj.group(0)
        return "- " + matchContent

    translatedLinkRegex = "(?<=\n)\[.*\]\(.*\)(?=\n)"
    newContent = re.sub(translatedLinkRegex, PrependLinkbullets, content)
    return newContent


def TranslateFile(remarkupFilePath):
    infile = open(remarkupFilePath, "r")
    remarkup = infile.read()
    infile.close()
    markdown = ""
    #print("Remarkup: \n" + remarkup)
    markdown = TranslateHeaders(remarkup)
    #print("-----------------------------------------------------------------------------------------")
    #print("Markdown after header replacement: \n" + markdown)

    baseFileName = remarkupFilePath[:-9]

    markdown = TranslateURLLinks(markdown, baseFileName)
    markdown = TranslateFileRefs(markdown)
    markdown = TranslateIcons(markdown)
    markdown = TranslateKeyDirectives(markdown)
    markdown = TranslatePastes(markdown)
    markdown = TranslateNavs(markdown)
    markdown = TranslateItalics(markdown)
    markdown = PrependBulletsOnSingleLineLinks(markdown)

    markdown += "\n "
    fullPath = baseFileName + ".markdown"
    #print(fullPath)
    if(os.path.exists(fullPath)):
        #print("    File already exists, removing: " + fullPath)
        os.remove(fullPath)

    outfile = open(fullPath, 'w')
    outfile.write(markdown)
    outfile.close()


fileExts = {}

# Set the directory you want to start from
rootDir = '.'
for dirName, subdirList, fileList in os.walk(rootDir):
    #print('Found directory: %s' % dirName)
    for fname in fileList:
        if(".remarkup" in fname):
            filePath = dirName + "\\" + fname
            if(os.path.exists(filePath[:-9] + ".markdown")):
                continue

            print("  File To Translate: " + fname)
            print("    FilePath: " + '\t%s' % filePath)
            TranslateFile(filePath)