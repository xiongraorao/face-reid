import dlib
import cv2
import numpy as np
import math


class Quaternoind:
    w = 0.0
    x = 0.0
    y = 0.0
    z = 0.0


face_detector = dlib.get_frontal_face_detector()

shape_predictor = dlib.shape_predictor("./model/shape_predictor_68_face_landmarks.dat")

# b, g, r = cv2.split(img)
# img2 = cv2.merge([r, g, b])

def pose(img):
    rows = img.shape[0]
    cols = img.shape[1]
    dets = face_detector(img, 1)
    for index, face in enumerate(dets):
        print('face {}; left {}; top {}; right {}; bottom {}'.format(index, face.left(), face.top(), face.right(),
                                                                     face.bottom()))
        cv2.rectangle(img, (face.left(), face.top()), (face.right(), face.bottom()), (0, 0, 255), 2)
        shape = shape_predictor(img, face)
        detect_result = shape.parts()
        '''
        鼻尖：30 
        下巴：8 
        左眼角：36 
        右眼角：45 
        左嘴角：48 
        右嘴角：54
        '''
        face_points = [detect_result[30], detect_result[8], detect_result[36], detect_result[45], detect_result[48],
                       detect_result[54]]
        landmarks = np.empty((1, 2), dtype=float)
        for i, pt in enumerate(face_points):
            pt_pos = (pt.x, pt.y)
            landmarks = np.append(landmarks, [[pt.x, pt.y]], axis=0)
            cv2.circle(img, pt_pos, 2, (255, 0, 0), 2)
        landmarks = np.delete(landmarks, 0, axis=0)

        # 定义人脸6个关键点的3D模型
        # 依次是，鼻子，下巴，左眼角，右眼角，左嘴角，右嘴角
        model_points = [(0.0, 0.0, 0.0), (0.0, -330.0, -65.0), (-225.0, 170.0, -135.0),
                        (225.0, 170.0, -135.0), (-150.0, -150.0, -125.0), (150.0, -150.0, -125.0)]
        model_points = np.asarray(model_points, dtype=float)

        # 利用solvePnP估计pose
        focal_length = cols
        center_x = cols / 2
        center_y = rows / 2
        camera_matrix = np.array([focal_length, 0, center_x, 0, focal_length, center_y, 0, 0, 1], dtype=float).reshape(
            3, 3)
        dist_coeffs = np.zeros((4, 1), dtype=float)
        retval, rotation_vector, translation_vector = cv2.solvePnP(model_points, landmarks, camera_matrix, dist_coeffs)

        #  旋转向量转化成欧拉角

        # 1. 生成四元数
        theta = cv2.norm(rotation_vector, cv2.NORM_L2)
        w = math.cos(theta / 2)
        x = math.sin(theta / 2) * rotation_vector[0,0] / theta
        y = math.sin(theta / 2) * rotation_vector[1,0] / theta
        z = math.sin(theta / 2) * rotation_vector[2,0] / theta

        # 2. 算欧拉角
        yy = y*y

        # pitch (x-axis rotation)
        t0 = 2.0 * (w*x + y*z)
        t1 = 1.0 - 2.0 * (x*x+yy)
        pitch = math.atan2(t0, t1)

        # yaw(y-axis rotation)
        t2 = 2.0 * (w * y - z * x)
        t2 = 1.0 if t2 > 1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        yaw = math.asin(t2)

        # roll (z-axis rotation)
        t3 = 2.0 * (w * z + x * y)
        t4 = 1.0 - 2.0 * (yy + z*z)
        roll = math.atan2(t3, t4)

        print("pitch: {} yaw: {} roll: {}".format(pitch, yaw, roll))

        cv2.putText(img, "pitch: " + str(pitch), (int(2*cols/3), 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,0,0),2)
        cv2.putText(img, "yaw: " + str(yaw), (int(2*cols/3), 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,0,0),2)
        cv2.putText(img, "roll: " + str(roll), (int(2*cols/3), 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,0,0),2)
        return img
    cv2.putText(img, "Cannot detect faces!", (int(2*cols/3), 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,0,0),2)
    return img
if __name__ == "__main__":
    img = cv2.imread("F:\\01.jpg")
    pose(img)
    cv2.namedWindow("test", cv2.WINDOW_AUTOSIZE)
    cv2.imshow("test", img)
    cv2.waitKey(0)