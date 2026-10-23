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

CLASS_LIST_FILENAME = 'classes.txt'
UNKNOWN_CLASS_PREFIX = 'class'


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


def unknown_class_name(index):
    return '{0}{1}'.format(UNKNOWN_CLASS_PREFIX, index)


def find_class_list_path(annot_path=None, img_path=None, extra_dirs=None):
    """Look for the classes.txt that belongs to an annotation or an image.

    A yolo file only stores class indexes, the names live in a classes.txt.
    Datasets keep that file next to the annotations, next to the images or in
    the root of the dataset, so all of those places are tried before giving up.
    """
    candidates = []

    def add_dir(directory):
        directory = os.path.abspath(directory)
        # The directory itself and the two above it.
        for _ in range(3):
            candidate = os.path.join(directory, CLASS_LIST_FILENAME)
            if candidate not in candidates:
                candidates.append(candidate)
            parent = os.path.dirname(directory)
            if parent == directory:
                break
            directory = parent

    for path in (annot_path, img_path):
        if path:
            add_dir(os.path.dirname(path))
    for directory in extra_dirs or []:
        if directory:
            add_dir(directory)

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def read_lines(file_path):
    """Read a text file without failing on the encoding of another tool."""
    for encoding in ('utf-8-sig', None):
        try:
            with codecs.open(file_path, 'r', encoding=encoding) as text_file:
                return text_file.read().splitlines()
        except UnicodeDecodeError:
            continue
        except (IOError, OSError) as e:
            print('Failed to read {0}: {1}'.format(file_path, e))
            return []

    # A damaged line is better than losing the whole annotation.
    with codecs.open(file_path, 'r', encoding='utf-8', errors='replace') as text_file:
        return text_file.read().splitlines()


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

    def __init__(self, file_path, image, class_list_path=None, img_path=None,
                 extra_class_dirs=None):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.file_path = file_path
        self.warnings = []

        if class_list_path is None:
            class_list_path = find_class_list_path(file_path, img_path, extra_class_dirs)

        self.class_list_path = class_list_path
        self.classes = read_class_list(class_list_path)
        if not self.classes:
            self.warn('No class list was found for {0}: classes are named after '
                      'their index.'.format(file_path))

        img_size = [image.height(), image.width(),
                    1 if image.isGrayscale() else 3]

        self.img_size = img_size

        self.verified = False
        self.parse_yolo_format()

    def warn(self, message):
        """Remember a problem of the annotation instead of hiding it."""
        if message not in self.warnings:
            self.warnings.append(message)
        print(message)

    def get_shapes(self):
        return self.shapes

    def get_class_list(self):
        """The class names in the order of their index."""
        return list(self.classes)

    def class_name(self, index):
        if index >= len(self.classes):
            # A box is never dropped because the class list is too short. The
            # missing classes keep their index, so the annotation can be fixed
            # instead of silently disappearing.
            self.warn('Class index {0} is missing from {1}.'.format(
                index, self.class_list_path or CLASS_LIST_FILENAME))
            self.classes.extend(
                unknown_class_name(i) for i in range(len(self.classes), index + 1))
        return self.classes[index]

    def add_shape(self, label, x_min, y_min, x_max, y_max, difficult):

        points = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
        self.shapes.append((label, points, None, None, difficult))

    def yolo_line_to_shape(self, class_index, x_center, y_center, w, h):
        try:
            index = int(class_index)
            x_center, y_center, w, h = [float(value) for value in (x_center, y_center, w, h)]
        except ValueError:
            self.warn('Invalid yolo values in {0}: {1} {2} {3} {4} {5}'.format(
                self.file_path, class_index, x_center, y_center, w, h))
            return None

        if not all(math.isfinite(value) for value in (x_center, y_center, w, h)):
            self.warn('Non-finite yolo values in {0}: {1} {2} {3} {4} {5}'.format(
                self.file_path, class_index, x_center, y_center, w, h))
            return None

        if index < 0:
            self.warn('Negative class index {0} in {1}.'.format(index, self.file_path))
            return None

        label = self.class_name(index)

        x_min = max(x_center - w / 2, 0)
        x_max = min(x_center + w / 2, 1)
        y_min = max(y_center - h / 2, 0)
        y_max = min(y_center + h / 2, 1)

        x_min = round(self.img_size[1] * x_min)
        x_max = round(self.img_size[1] * x_max)
        y_min = round(self.img_size[0] * y_min)
        y_max = round(self.img_size[0] * y_max)

        return label, x_min, y_min, x_max, y_max

    def polygon_line_to_shape(self, fields):
        """Use the frame of a yolo segmentation polygon as a bounding box."""
        try:
            values = [float(value) for value in fields[1:]]
        except ValueError:
            self.warn('Invalid yolo values in {0}: {1}'.format(
                self.file_path, ' '.join(fields)))
            return None

        if not all(math.isfinite(value) for value in values):
            self.warn('Non-finite yolo values in {0}.'.format(self.file_path))
            return None

        x_values = values[0::2]
        y_values = values[1::2]
        return self.yolo_line_to_shape(
            fields[0],
            (min(x_values) + max(x_values)) / 2, (min(y_values) + max(y_values)) / 2,
            max(x_values) - min(x_values), max(y_values) - min(y_values))

    def parse_yolo_format(self):
        if not os.path.isfile(self.file_path):
            self.warn('Annotation file not found: {0}'.format(self.file_path))
            return

        for line_number, bnd_box in enumerate(read_lines(self.file_path), start=1):
            # Values are separated by whitespace, blank lines are allowed.
            fields = bnd_box.split()
            if not fields:
                continue

            if len(fields) == 5:
                shape = self.yolo_line_to_shape(*fields)
            elif len(fields) > 5 and (len(fields) - 1) % 2 == 0:
                # Losing the annotation of a polygon would drop it from the
                # file the next time it is saved, so keep its frame.
                self.warn('Line {0} of {1} is a polygon, its frame is used '
                          'instead.'.format(line_number, self.file_path))
                shape = self.polygon_line_to_shape(fields)
            else:
                self.warn('Skipping line {0} of {1}: {2} values instead of '
                          '5.'.format(line_number, self.file_path, len(fields)))
                continue

            if shape is None:
                continue

            label, x_min, y_min, x_max, y_max = shape
            # Caveat: difficult flag is discarded when saved as yolo format.
            self.add_shape(label, x_min, y_min, x_max, y_max, False)
