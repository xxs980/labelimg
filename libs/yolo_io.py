#!/usr/bin/env python
# -*- coding: utf8 -*-
import math
import sys
import os
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
from libs.constants import DEFAULT_ENCODING

TXT_EXT = '.txt'
ENCODE_METHOD = DEFAULT_ENCODING


def read_class_list(class_list_path):
    """Read the class names of a yolo dataset, tolerating odd encodings."""
    if not class_list_path or not os.path.isfile(class_list_path):
        return []

    try:
        with codecs.open(class_list_path, 'r', encoding='utf-8-sig') as class_file:
            content = class_file.read()
    except UnicodeDecodeError:
        # classes.txt used to be written with the encoding of the machine.
        try:
            with open(class_list_path, 'r') as class_file:
                content = class_file.read()
        except (UnicodeDecodeError, OSError) as e:
            print('Failed to read the class list {0}: {1}'.format(class_list_path, e))
            return []
    except OSError as e:
        print('Failed to read the class list {0}: {1}'.format(class_list_path, e))
        return []

    return [line.strip() for line in content.splitlines() if line.strip()]


class YOLOWriter:

    def __init__(self, folder_name, filename, img_size, database_src='Unknown', local_img_path=None):
        self.folder_name = folder_name
        self.filename = filename
        self.database_src = database_src
        self.img_size = img_size
        self.box_list = []
        self.local_img_path = local_img_path
        self.verified = False

    def add_bnd_box(self, x_min, y_min, x_max, y_max, name, difficult):
        bnd_box = {'xmin': x_min, 'ymin': y_min, 'xmax': x_max, 'ymax': y_max}
        bnd_box['name'] = name
        bnd_box['difficult'] = difficult
        self.box_list.append(bnd_box)

    def bnd_box_to_yolo_line(self, box, class_list=[]):
        x_min = box['xmin']
        x_max = box['xmax']
        y_min = box['ymin']
        y_max = box['ymax']

        x_center = float((x_min + x_max)) / 2 / self.img_size[1]
        y_center = float((y_min + y_max)) / 2 / self.img_size[0]

        w = float((x_max - x_min)) / self.img_size[1]
        h = float((y_max - y_min)) / self.img_size[0]

        # PR387
        box_name = box['name']
        if box_name not in class_list:
            class_list.append(box_name)

        class_index = class_list.index(box_name)

        return class_index, x_center, y_center, w, h

    def save(self, class_list=[], target_file=None):
        if self.img_size[0] <= 0 or self.img_size[1] <= 0:
            raise ValueError('Cannot save {0} in yolo format, the size of the image is unknown: '
                             '{1}'.format(self.filename, self.img_size))

        out_file = None  # Update yolo .txt
        out_class_file = None   # Update class list .txt

        if target_file is None:
            out_file = open(
            self.filename + TXT_EXT, 'w', encoding=ENCODE_METHOD)
            classes_file = os.path.join(os.path.dirname(os.path.abspath(self.filename)), "classes.txt")
            out_class_file = codecs.open(classes_file, 'w', encoding=ENCODE_METHOD)

        else:
            out_file = codecs.open(target_file, 'w', encoding=ENCODE_METHOD)
            classes_file = os.path.join(os.path.dirname(os.path.abspath(target_file)), "classes.txt")
            out_class_file = codecs.open(classes_file, 'w', encoding=ENCODE_METHOD)


        for box in self.box_list:
            class_index, x_center, y_center, w, h = self.bnd_box_to_yolo_line(box, class_list)
            # print (classIndex, x_center, y_center, w, h)
            out_file.write("%d %.6f %.6f %.6f %.6f\n" % (class_index, x_center, y_center, w, h))

        # print (classList)
        # print (out_class_file)
        for c in class_list:
            out_class_file.write(c+'\n')

        out_class_file.close()
        out_file.close()



class YoloReader:

    def __init__(self, file_path, image, class_list_path=None):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.file_path = file_path

        if class_list_path is None:
            dir_path = os.path.dirname(os.path.realpath(self.file_path))
            self.class_list_path = os.path.join(dir_path, "classes.txt")
        else:
            self.class_list_path = class_list_path

        # print (file_path, self.class_list_path)

        self.classes = read_class_list(self.class_list_path)

        # print (self.classes)

        img_size = [image.height(), image.width(),
                    1 if image.isGrayscale() else 3]

        self.img_size = img_size

        self.verified = False
        # try:
        self.parse_yolo_format()
        # except:
        #     pass

    def get_shapes(self):
        return self.shapes

    def add_shape(self, label, x_min, y_min, x_max, y_max, difficult):

        points = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
        self.shapes.append((label, points, None, None, difficult))

    def yolo_line_to_shape(self, class_index, x_center, y_center, w, h):
        try:
            index = int(class_index)
            x_center, y_center, w, h = [float(value) for value in (x_center, y_center, w, h)]
        except ValueError:
            print('Invalid yolo values in {0}: {1} {2} {3} {4} {5}'.format(
                self.file_path, class_index, x_center, y_center, w, h))
            return None

        if not all(math.isfinite(value) for value in (x_center, y_center, w, h)):
            print('Non-finite yolo values in {0}: {1} {2} {3} {4} {5}'.format(
                self.file_path, class_index, x_center, y_center, w, h))
            return None

        if not 0 <= index < len(self.classes):
            print('Unknown class index {0} in {1}: only {2} classes are known.'.format(
                index, self.file_path, len(self.classes)))
            return None

        label = self.classes[index]

        x_min = max(x_center - w / 2, 0)
        x_max = min(x_center + w / 2, 1)
        y_min = max(y_center - h / 2, 0)
        y_max = min(y_center + h / 2, 1)

        x_min = round(self.img_size[1] * x_min)
        x_max = round(self.img_size[1] * x_max)
        y_min = round(self.img_size[0] * y_min)
        y_max = round(self.img_size[0] * y_max)

        return label, x_min, y_min, x_max, y_max

    def parse_yolo_format(self):
        if not os.path.isfile(self.file_path):
            print('Annotation file not found: {0}'.format(self.file_path))
            return

        with codecs.open(self.file_path, 'r', encoding='utf-8-sig') as bnd_box_file:
            for line_number, bnd_box in enumerate(bnd_box_file, start=1):
                # Values are separated by whitespace, blank lines are allowed.
                fields = bnd_box.split()
                if not fields:
                    continue

                if len(fields) != 5:
                    print('Skipping line {0} of {1}: expected 5 values, got {2}.'.format(
                        line_number, self.file_path, len(fields)))
                    continue

                shape = self.yolo_line_to_shape(*fields)
                if shape is None:
                    continue

                label, x_min, y_min, x_max, y_max = shape
                # Caveat: difficult flag is discarded when saved as yolo format.
                self.add_shape(label, x_min, y_min, x_max, y_max, False)
