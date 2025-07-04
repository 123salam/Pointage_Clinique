import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime
path=r'C:\Users\user\Desktop\base'
image = []
classeNames = []
myList= os.listdir(path)
print(myList)
for cl in myList :
    curImg = cv2.imread(f'{path}/{cl}')
    image.append(curImg)
    classeNames.append(os.path.splitext(cl)[0])
print(classeNames)

def findEncodings(image):
    encodeList = []
    for img in  image:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

def markAttendence(name, dtString=None):
    with open(r'C:\Users\user\Desktop\Projet\AttendenceProject.csv','r+') as f:
        myDataList = f.readlines()
        nameList = []
        for line in myDataList:
            entry = line.split(',')
            nameList.append(entry[0])
        if name not in nameList:
            now = datetime.now()
            dtString = now.strftime('%H:%M:%S')
            f.writelines(f'\n{name},{dtString}')



encodeListKnown = findEncodings(image)
print('Encoding Complete')

cap = cv2.VideoCapture(0)

while True:
    success,img = cap.read()
    imgs = cv2.resize(img,(0,0),None,0.25,0.25)
    imgs = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)


    facesCurFrame = face_recognition.face_locations(img)
    encodeCurFrame = face_recognition.face_encodings(img,facesCurFrame)

    for encodeFace , faceLoc in zip(encodeCurFrame, facesCurFrame):
        matches = face_recognition.compare_faces(encodeListKnown,encodeFace)
        faceDis = face_recognition.face_distance(encodeListKnown,encodeFace)
        print(faceDis)
        matchindex= np.argmin(faceDis)

        if matches[matchindex]:
            name = classeNames[matchindex].upper()
            print(name)
            y1,x2,y2,x1= faceLoc

            cv2.rectangle(img,(x1,y1),(x2,y2),(255,0,255),2)
            cv2.rectangle(img,(x1,y2-35),(x2,y2),(255,0,255),cv2.FILLED)
            cv2.putText(img, name,(x1+6,y2-6),cv2.FONT_HERSHEY_COMPLEX,1,(255,255,255),2)
            markAttendence(name)


    cv2.imshow('webcam' , img)
    cv2.waitKey(1)