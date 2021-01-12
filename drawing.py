import cv2
import numpy as np

def show(img_name, img, waitKey=0):
    cv2.namedWindow(img_name, cv2.WINDOW_NORMAL)
    cv2.imshow(img_name, img)
    cv2.waitKey(waitKey)

def update_packages(packages: dict):
    img = np.zeros((200, 400, 3))
    for i, (id, data) in enumerate(packages.items()):
        txt = f'{id}: {data["status"]}'
        if data['executor']:
            txt += f' {data["executor"]}'

        img = cv2.putText(img, txt, (10, (i +1) * 20), 1, 1, (0, 255, 0), 1)
    return img

def update_messages(messages):
    img = np.zeros((200, 800, 3))
    for i, msg in enumerate(messages):
        img = cv2.putText(img, f'{msg}', (10, (i +1) * 20), 1, 1, (0, 255, 0), 1)
    return img

def update_positions(positions):
    img = np.zeros((200, 1200, 3))


    for i, (id, distance) in enumerate(positions.items()):
        x1 = 200 * (i + 1)
        y1 = 40

        bar_height = 100
        img = cv2.rectangle(img, (x1, y1), (x1 + 30, y1 + bar_height), (0, 255, 255), 2)
        img = cv2.rectangle(img, (x1, y1), (x1 + 30, y1 + int(bar_height * distance)), (0, 255, 255), -1)

        img = cv2.putText(img, f'{id}', (x1 - 20, y1 + bar_height + 20), 1, 1, (0, 255, 0), 1)
    return img
