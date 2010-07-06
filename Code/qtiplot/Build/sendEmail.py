import re
import smtplib
import socket
import os
import sys
import platform
import subprocess as sp
from shutil import move
sys.path.insert(0,'../Mantid/Build')
import buildNotification as notifier
from time import strftime
import urllib2
import time

def RecordExists():
    url = base_url + "rec_exists.psp?id=" + str(SvnID)
    try:
        f = urllib2.urlopen(url)
        page = f.read()
        if re.search("Success", page):
            r = True
        elif re.search("Failure", page):
            r = False
        else:
            r = False #needs something better here, but it *should* be controlled by the db
    except urllib2.HTTPError:
        r = False
    return r
#end of RecordExists

def CreateRecord():
    url = base_url + "rec_create.psp?id=" + str(SvnID)
    try:
        f = urllib2.urlopen(url)
        return True
    except urllib2.HTTPError:
        return False
#end of CreateRecord()

project = 'qtiplot'
base_url = notifier.base_url

#Email settings
SENDER = platform.system() 
#Create Subject
subject = 'Subject: ' + platform.system()
if platform.architecture()[0] == '64bit':
    SENDER += '64'
    subject += '64'
SENDER += 'BuildServer1@mantidproject.org'
subject += ' Build Report: '

#Set up email content 
buildSuccess = True

remoteArchiveDir, relativeLogDir = notifier.getArchiveDir(project)
localBaseLog = '../../../../logs/' 
localLogDir = localBaseLog + project + '/'

#Get build result and errors
fileBuild = localLogDir+'build.log'
f = open(fileBuild,'r')

for line in f:
     buildResult = line
     
f.close()
notifier.moveToArchive(fileBuild,remoteArchiveDir)

if 'failed' in buildResult:
     buildSuccess = False	
	
fileBuildErr = localLogDir+'error.log'
notifier.moveToArchive(fileBuildErr,remoteArchiveDir)

mtdtests = localBaseLog + 'Mantid' + '/MantidTests.txt'
f = open(mtdtests, 'r')
for line in f:
     mtdTestsResult = line
f.close()
if 'False' in mtdTestsResult:
     mtdTestsPassed = False
else:
     mtdTestsPassed = True

if buildSuccess and mtdTestsPassed:
     fileLaunchInstaller = localLogDir + 'LaunchInstaller.txt'
     f = open(fileLaunchInstaller,'w')
     f.write('launch')

last = localLogDir + 'lastBuild.txt'
try:
     lastBuild = open(last,'r').read()
except IOError:
     lastBuild = 'False'
open(last,'w').write(str(buildSuccess))

#get time taken to build
fileBuildTime = localLogDir + 'timebuild.log'
try:
    f = open(fileBuildTime, 'r')
    buildTime = float(f.read())
    f.close()
    notifier.moveToArchive(fileBuildTime, remoteArchiveDir)
except IOError:
    buildTime = -1.0

# get SvnID
SvnID = notifier.getSVNRevision()

if not RecordExists():
    CreateRecord()

#build url for use in query
url = base_url + 'nfwd.psp?id=' + str(SvnID) + '&project=' + project
url += '&platform=' + platform.system() + platform.architecture()[0][:2]
url += '&result=' + str(buildSuccess) + '&time=' + str(buildTime)
# open url
try:
    f = urllib2.urlopen(url)
    time.sleep(0.1)
except urllib2.HTTPError:
    pass


# We want to skip sending email if this AND previous build succeeded
if buildSuccess and lastBuild=='True':
     sys.exit(0)

#Construct Message
httpLinkToArchive = 'http://download.mantidproject.org/' + relativeLogDir.replace("\\","/")

message = 'Build Completed at: ' + strftime("%H:%M:%S %d-%m-%Y") + "\n"
message += 'MantidPlot Build Passed: ' + str(buildSuccess) + "\n\n"
message += '-----------------------------------------------------------------------\n'
message += 'MANTIDPLOT BUILD LOG\n\n'
message += 'Build stdout <' + httpLinkToArchive + 'build.log>\n'
message += 'Build stderr <' + httpLinkToArchive + 'error.log>\n'

if buildSuccess:
	subject += '[MantidPlot Build Successful]\n\n\n'
else:
	subject += '[MantidPlot Build Failed]\n\n\n'

# Send mail
logfile = notifier.sendResultMail(subject+message,localLogDir,sender=SENDER)
notifier.moveToArchive(logfile,remoteArchiveDir)

if buildSuccess:
     sys.exit(0)
else:
     sys.exit(1)
