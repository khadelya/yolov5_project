import numpy as np
from sklearn.model_selection import train_test_split
import shutil
import os

path_to_labels_train = "../data/labels/train"
path_to_images_train = "../data/images/train"
path_to_labels_val = "../data/labels/val"
path_to_images_val = "../data/images/val"

files = os.listdir(path=path_to_labels_train)

files_test, files_val = train_test_split(files, train_size=0.8)

for file in files:
    if file in files_val:
        source_tif = os.path.join(path_to_images_train, file.replace("txt", "tif"))
        source_txt = os.path.join(path_to_labels_train, file)
        destination_tif = os.path.join(path_to_images_val, file.replace("txt", "tif"))
        destination_txt = os.path.join(path_to_labels_val, file)
        shutil.move(source_tif, destination_tif)
        shutil.move(source_txt, destination_txt)
