import sys
import time
import uuid

import cv2

from config import camera
from util import Face, mat_to_base64, base64_to_mat

(major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')


def track_test():
    # video = cv2.VideoCapture(0)
    video = cv2.VideoCapture(camera['dev'])
    face_tool = Face('tcp://192.168.1.11:5559')
    while True:
        t1 = time.time()
        ok, frame = video.read()
        if not ok:
            break
        b64 = mat_to_base64(frame)
        face = face_tool.detect(b64, field='track', camera_id=str(0))
        print('track num: ', face['track_nums'])
        for num in range(face['track_nums']):
            face_b64 = face['track'][num]['image_base64']
            mat = base64_to_mat(face_b64)
            cv2.imwrite('F:\\output\\' + str(uuid.uuid4()) + '.jpg', mat)
        print('cost time: ', round((time.time() - t1) * 1000))
        # cv2.imshow('origin', frame)
        # k = cv2.waitKey(1) & 0xff
        # if k == 27: break


def single_track(tracker_type):
    if int(minor_ver) < 3:
        tracker = cv2.Tracker_create(tracker_type)
    else:
        if tracker_type == 'BOOSTING':
            tracker = cv2.TrackerBoosting_create()
        if tracker_type == 'MIL':
            tracker = cv2.TrackerMIL_create()
        if tracker_type == 'KCF':
            tracker = cv2.TrackerKCF_create()
        if tracker_type == 'TLD':
            tracker = cv2.TrackerTLD_create()
        if tracker_type == 'MEDIANFLOW':
            tracker = cv2.TrackerMedianFlow_create()
        if tracker_type == 'GOTURN':
            tracker = cv2.TrackerGOTURN_create()
        if tracker_type == 'MOSSE':
            tracker = cv2.TrackerMOSSE_create()
        if tracker_type == "CSRT":
            tracker = cv2.TrackerCSRT_create()
    video = cv2.VideoCapture(0)
    if not video.isOpened():
        print('Cound not open video')
        sys.exit()

    ok, frame = video.read()
    # Uncomment the line below to select a different bounding box
    bbox = cv2.selectROI(frame, False)
    print('ROI, ', bbox)

    # Initialize tracker with first frame and bounding box
    ok = tracker.init(frame, bbox)

    print('tracker initialize ', ok)

    while True:
        # Read a new frame
        ok, frame = video.read()
        if not ok:
            break

        # Start timer
        timer = cv2.getTickCount()

        # Update tracker
        ok, bbox = tracker.update(frame)

        # Calculate Frames per second (FPS)
        fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer);

        # Draw bounding box
        if ok:
            # Tracking success
            p1 = (int(bbox[0]), int(bbox[1]))
            p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
        else:
            # Tracking failure
            cv2.putText(frame, "Tracking failure detected", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            print('跟踪结束')
            bbox = (61, 58, 229, 315)
            tracker.init(frame, bbox)
            continue

        # Display tracker type on frame
        cv2.putText(frame, tracker_type + " Tracker", (100, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);

        # Display FPS on frame
        cv2.putText(frame, "FPS : " + str(int(fps)), (100, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);

        # Display result
        cv2.imshow("Tracking", frame)

        # Exit if ESC pressed
        k = cv2.waitKey(1) & 0xff
        if k == 27: break


def multi_track():
    tracker = cv2.MultiTracker_create()
    video = cv2.VideoCapture(0)
    if not video.isOpened():
        print('Cound not open video')
        sys.exit()

    ok, frame = video.read()
    # Uncomment the line below to select a different bounding box
    bbox1 = cv2.selectROI(frame, False)
    bbox2 = cv2.selectROI(frame, False)

    ok = tracker.add(cv2.TrackerKCF_create(), frame, bbox1)
    ok = tracker.add(cv2.TrackerKCF_create(), frame, bbox2)

    print('tracker initialize ', ok)

    while True:
        # Read a new frame
        ok, frame = video.read()
        if not ok:
            break

        # Start timer
        timer = cv2.getTickCount()

        # Update tracker
        ok, bboxs = tracker.update(frame)

        # Calculate Frames per second (FPS)
        fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer);

        print(ok, bboxs)

        # Draw bounding box
        if ok:
            # Tracking success
            for bbox in bboxs:
                p1 = (int(bbox[0]), int(bbox[1]))
                p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
        else:
            # Tracking failure
            cv2.putText(frame, "Tracking failure detected", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            print('跟踪结束')

        # Display tracker type on frame
        cv2.putText(frame, "KCF" + " Tracker", (100, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);

        # Display FPS on frame
        cv2.putText(frame, "FPS : " + str(int(fps)), (100, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);

        # Display result
        cv2.imshow("Tracking", frame)

        # Exit if ESC pressed
        k = cv2.waitKey(1) & 0xff
        if k == 27: break


track_test()
