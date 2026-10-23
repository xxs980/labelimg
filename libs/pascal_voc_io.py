#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
import locale
import re
from libs.constants import DEFAULT_ENCODING
from libs.ustr import ustr


XML_EXT = '.xml'
ENCODE_METHOD = DEFAULT_ENCODING

class PascalVocWriter:

    def __init__(self, folder_name, filename, img_size, database_src='Unknown', local_img_path=None):
        self.folder_name = folder_name
        self.filename = filename
        self.database_src = database_src
        self.img_size = img_size
        self.box_list = []
        self.local_img_path = local_img_path
        self.verified = False

    def prettify(self, elem):
        """
            Return a pretty-printed XML string for the Element.
        """
        rough_string = ElementTree.tostring(elem, 'utf8')
        root = etree.fromstring(rough_string)
        return etree.tostring(root, pretty_print=True, encoding=ENCODE_METHOD).replace("  ".encode(), "\t".encode())
        # minidom does not support UTF-8
        # reparsed = minidom.parseString(rough_string)
        # return reparsed.toprettyxml(indent="\t", encoding=ENCODE_METHOD)

    def gen_xml(self):
        """
            Return XML root
        """
        # Check conditions
        if self.filename is None or \
                self.folder_name is None or \
                self.img_size is None:
            return None

        top = Element('annotation')
        if self.verified:
            top.set('verified', 'yes')

        folder = SubElement(top, 'folder')
        folder.text = self.folder_name

        filename = SubElement(top, 'filename')
        filename.text = self.filename

        if self.local_img_path is not None:
            local_img_path = SubElement(top, 'path')
            local_img_path.text = self.local_img_path

        source = SubElement(top, 'source')
        database = SubElement(source, 'database')
        database.text = self.database_src

        size_part = SubElement(top, 'size')
        width = SubElement(size_part, 'width')
        height = SubElement(size_part, 'height')
        depth = SubElement(size_part, 'depth')
        width.text = str(self.img_size[1])
        height.text = str(self.img_size[0])
        if len(self.img_size) == 3:
            depth.text = str(self.img_size[2])
        else:
            depth.text = '1'

        segmented = SubElement(top, 'segmented')
        segmented.text = '0'
        return top

    def add_bnd_box(self, x_min, y_min, x_max, y_max, name, difficult):
        bnd_box = {'xmin': x_min, 'ymin': y_min, 'xmax': x_max, 'ymax': y_max}
        bnd_box['name'] = name
        bnd_box['difficult'] = difficult
        self.box_list.append(bnd_box)

    def append_objects(self, top):
        for each_object in self.box_list:
            object_item = SubElement(top, 'object')
            name = SubElement(object_item, 'name')
            name.text = ustr(each_object['name'])
            pose = SubElement(object_item, 'pose')
            pose.text = "Unspecified"
            truncated = SubElement(object_item, 'truncated')
            if int(float(each_object['ymax'])) == int(float(self.img_size[0])) or (int(float(each_object['ymin'])) == 1):
                truncated.text = "1"  # max == height or min
            elif (int(float(each_object['xmax'])) == int(float(self.img_size[1]))) or (int(float(each_object['xmin'])) == 1):
                truncated.text = "1"  # max == width or min
            else:
                truncated.text = "0"
            difficult = SubElement(object_item, 'difficult')
            difficult.text = str(bool(each_object['difficult']) & 1)
            bnd_box = SubElement(object_item, 'bndbox')
            x_min = SubElement(bnd_box, 'xmin')
            x_min.text = str(each_object['xmin'])
            y_min = SubElement(bnd_box, 'ymin')
            y_min.text = str(each_object['ymin'])
            x_max = SubElement(bnd_box, 'xmax')
            x_max.text = str(each_object['xmax'])
            y_max = SubElement(bnd_box, 'ymax')
            y_max.text = str(each_object['ymax'])

    def save(self, target_file=None):
        root = self.gen_xml()
        if root is None:
            raise ValueError('Cannot save an incomplete annotation: {0}'.format(target_file or self.filename))

        self.append_objects(root)
        out_file = None
        if target_file is None:
            out_file = codecs.open(
                self.filename + XML_EXT, 'w', encoding=ENCODE_METHOD)
        else:
            out_file = codecs.open(target_file, 'w', encoding=ENCODE_METHOD)

        prettify_result = self.prettify(root)
        out_file.write(prettify_result.decode('utf8'))
        out_file.close()


class PascalVocReader:

    def __init__(self, file_path):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.file_path = file_path
        self.verified = False
        self.warnings = []
        try:
            self.parse_xml()
        except Exception as e:
            # A broken annotation must not keep the image from opening.
            self.warn('Failed to read {0}: {1}'.format(file_path, e))

    def get_shapes(self):
        return self.shapes

    def warn(self, message):
        """Remember a problem of the annotation instead of hiding it."""
        if message not in self.warnings:
            self.warnings.append(message)
        print(message)

    def read_tree(self):
        """Parse the file, tolerating what another tool left behind."""
        with open(self.file_path, 'rb') as xml_file:
            content = xml_file.read()

        try:
            return etree.fromstring(content, etree.XMLParser(encoding=ENCODE_METHOD))
        except etree.XMLSyntaxError:
            pass

        # Such a file claims an encoding that its bytes do not hold, or it is
        # cut short. The bounding boxes of it are still usable.
        for encoding in (ENCODE_METHOD, locale.getpreferredencoding(False)):
            try:
                text = content.decode(encoding)
            except (LookupError, TypeError, UnicodeDecodeError):
                continue
            text = re.sub(r'^\s*<\?xml[^>]*\?>', '', text)
            try:
                parser = etree.XMLParser(encoding=ENCODE_METHOD, recover=True)
                return etree.fromstring(text.encode('utf-8'), parser)
            except etree.XMLSyntaxError:
                continue

        raise ValueError('unsupported or damaged xml file')

    def read_difficult(self, object_iter):
        """Read the difficult flag, which the tools write in different ways."""
        node = object_iter.find('difficult')
        text = ustr(node.text).strip() if node is not None and node.text else ''
        if text in ('1', 'true', 'yes'):
            return True
        if text and text not in ('0', 'false', 'no'):
            self.warn('Invalid difficult flag {0} in {1}.'.format(text, self.file_path))
        return False

    def add_shape(self, label, bnd_box, difficult):
        if bnd_box is None:
            raise ValueError('the object has no bndbox')

        x_min = self.read_coordinate(bnd_box, 'xmin')
        y_min = self.read_coordinate(bnd_box, 'ymin')
        x_max = self.read_coordinate(bnd_box, 'xmax')
        y_max = self.read_coordinate(bnd_box, 'ymax')
        points = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
        self.shapes.append((label, points, None, None, difficult))

    @staticmethod
    def read_coordinate(bnd_box, name):
        node = bnd_box.find(name)
        text = ustr(node.text).strip() if node is not None and node.text else ''
        try:
            return int(round(float(text)))
        except ValueError:
            raise ValueError('the value of {0} is missing or is not a number'.format(name))

    def parse_xml(self):
        if not self.file_path.endswith(XML_EXT):
            raise ValueError('unsupported file format: {0}'.format(self.file_path))

        xml_tree = self.read_tree()
        self.verified = xml_tree.attrib.get('verified') == 'yes'

        objects = xml_tree.findall('object')
        for index, object_iter in enumerate(objects, start=1):
            try:
                name = object_iter.find('name')
                label = ustr(name.text).strip() if name is not None and name.text else ''
                # Add chris
                self.add_shape(label, object_iter.find('bndbox'),
                               self.read_difficult(object_iter))
            except (AttributeError, TypeError, ValueError) as e:
                # One damaged object must not hide the boxes of the others.
                self.warn('Skipping object {0} of {1}: {2}'.format(index, self.file_path, e))

        if objects and not self.shapes:
            self.warn('No bounding box could be read from {0}.'.format(self.file_path))
        return True
