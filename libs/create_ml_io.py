#!/usr/bin/env python
# -*- coding: utf8 -*-
import codecs
import json
import math
import shutil
from pathlib import Path

from libs.constants import DEFAULT_ENCODING
import os

JSON_EXT = '.json'
ENCODE_METHOD = DEFAULT_ENCODING


class CreateMLWriter:
    def __init__(self, folder_name, filename, img_size, shapes, output_file, database_src='Unknown', local_img_path=None):
        self.folder_name = folder_name
        self.filename = filename
        self.database_src = database_src
        self.img_size = img_size
        self.box_list = []
        self.local_img_path = local_img_path
        self.verified = False
        self.shapes = shapes
        self.output_file = output_file

    def read_existing_annotations(self):
        """Load the annotations that are already stored in the output file."""
        if not os.path.isfile(self.output_file):
            return []

        with codecs.open(self.output_file, 'r', encoding=ENCODE_METHOD) as output_file:
            input_data = output_file.read()

        try:
            output_dict = json.loads(input_data)
        except ValueError:
            print('Failed to parse {0}, it is replaced and backed up.'.format(self.output_file))
            self.backup_output_file()
            return []

        # Files written by other tools do not necessarily hold a list.
        if not isinstance(output_dict, list):
            print('Unexpected content in {0}, it is replaced and backed up.'.format(self.output_file))
            self.backup_output_file()
            return []

        return [entry for entry in output_dict if isinstance(entry, dict)]

    def backup_output_file(self):
        backup_file = self.output_file + '.bak'
        try:
            shutil.copyfile(self.output_file, backup_file)
            print('Previous annotations moved to {0}.'.format(backup_file))
        except (IOError, OSError) as e:
            print('Failed to back up {0}: {1}'.format(self.output_file, e))

    def write(self):
        output_dict = self.read_existing_annotations()

        output_image_dict = {
            "image": self.filename,
            "annotations": []
        }

        for shape in self.shapes:
            points = shape["points"]
            if not points:
                continue

            x_values = [point[0] for point in points]
            y_values = [point[1] for point in points]

            height, width, x, y = self.calculate_coordinates(min(x_values), max(x_values),
                                                             min(y_values), max(y_values))

            shape_dict = {
                "label": shape["label"],
                "coordinates": {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height
                }
            }
            output_image_dict["annotations"].append(shape_dict)

        # check if image already in output
        exists = False
        for i in range(0, len(output_dict)):
            if output_dict[i].get("image") == output_image_dict["image"]:
                exists = True
                output_dict[i] = output_image_dict
                break

        if not exists:
            output_dict.append(output_image_dict)

        Path(self.output_file).write_text(json.dumps(output_dict), ENCODE_METHOD)

    def calculate_coordinates(self, x1, x2, y1, y2):
        if x1 < x2:
            x_min = x1
            x_max = x2
        else:
            x_min = x2
            x_max = x1
        if y1 < y2:
            y_min = y1
            y_max = y2
        else:
            y_min = y2
            y_max = y1
        width = x_max - x_min
        if width < 0:
            width = width * -1
        height = y_max - y_min
        # x and y from center of rect
        x = x_min + width / 2
        y = y_min + height / 2
        return height, width, x, y


class CreateMLReader:
    def __init__(self, json_path, file_path):
        self.json_path = json_path
        self.shapes = []
        self.verified = False
        self.filename = os.path.basename(file_path)
        try:
            self.parse_json()
        except ValueError:
            print("JSON decoding failed")
        except (KeyError, TypeError) as e:
            print('Unexpected CreateML format in {0}: {1}'.format(self.json_path, e))

    def parse_json(self):
        with codecs.open(self.json_path, 'r', encoding=ENCODE_METHOD) as file:
            input_data = file.read()

        output_dict = json.loads(input_data)
        self.verified = True

        if len(self.shapes) > 0:
            self.shapes = []
        for image in output_dict:
            if not isinstance(image, dict) or image.get("image") != self.filename:
                continue
            for shape in image.get("annotations") or []:
                if not isinstance(shape, dict):
                    continue
                self.add_shape(shape["label"], shape["coordinates"])

    def add_shape(self, label, bnd_box):
        try:
            x = float(bnd_box["x"])
            y = float(bnd_box["y"])
            width = float(bnd_box["width"])
            height = float(bnd_box["height"])
        except (KeyError, TypeError, ValueError) as e:
            print('Skipping a CreateML annotation of {0}: {1}'.format(self.json_path, e))
            return

        if not all(math.isfinite(value) for value in (x, y, width, height)):
            print('Skipping non-finite CreateML coordinates in {0}.'.format(self.json_path))
            return

        x_min = x - (width / 2)
        y_min = y - (height / 2)

        x_max = x + (width / 2)
        y_max = y + (height / 2)

        points = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
        self.shapes.append((label, points, None, None, True))

    def get_shapes(self):
        return self.shapes
