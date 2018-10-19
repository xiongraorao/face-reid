from sys import argv

from PIL import Image

from util.face import get_list_files


def scale_image(height):
    """
    将图片按比例缩放到height高度
    :param height: 目标高度
    :return: no
    """
    images = get_list_files(argv[1])
    for img in images:
        image = Image.open(img)
        w, h = image.size
        scale = height * 1.0 / h
        width = int(scale * w)
        image = image.resize((width, height), Image.ANTIALIAS)
        image.save("F:\\datasets\\secretstar_normal\\" + img[-14:-4] + ".jpg")
        print("ok," + img)

if __name__ == '__main__':
    scale_image(300)