import base64
import json
import os

from util.face import face_feature, Face

base_dir = "F:\\datasets\\lfw"

def get_list_files(path):
    ret = []
    for root, dirs, files in os.walk(path):
        for filespath in files:
            ret.append(os.path.join(root, filespath))
    return ret

img_lists = get_list_files(base_dir)

lfw_file = open('lfw_feature.txt', 'w')

count = 1
face_tool = Face('tcp://192.168.1.11:5559')
for img in img_lists:
    print(img, 'count = ', count)
    f = open(img, 'rb')
    b64 = base64.b64encode(f.read()).decode('utf-8')
    feature = face_tool.feature(b64)
    result = {'path': img, 'feature': feature}
    lfw_file.write(json.dumps(result))
    lfw_file.flush()
    f.close()
    print(img, 'count = ', count)
    count += 1
lfw_file.flush()
lfw_file.close()