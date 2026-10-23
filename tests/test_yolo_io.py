import codecs
import os
import shutil
import sys
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5.QtGui import QImage

from libs.yolo_io import read_class_list
from libs.yolo_io import YOLOWriter
from libs.yolo_io import YoloReader

def make_image(path, width=100, height=50):
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(0xFFFFFFFF)
    image.save(path)
    return QImage(path)

class TestYoloReader(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix='labelImg-yolo-')
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)
        self.image_path = os.path.join(self.tmp_dir, 'img.png')
        self.image = make_image(self.image_path)
        self.txt_path = os.path.join(self.tmp_dir, 'img.txt')
        self.classes_path = os.path.join(self.tmp_dir, 'classes.txt')

    def write_classes(self, content, encoding='utf-8'):
        with codecs.open(self.classes_path, 'w', encoding=encoding) as classes_file:
            classes_file.write(content)

    def read_shapes(self):
        return YoloReader(self.txt_path, self.image).get_shapes()

    def test_reads_bounding_box(self):
        self.write_classes('cat\ndog\n')
        with open(self.txt_path, 'w') as txt_file:
            txt_file.write('0 0.5 0.5 0.2 0.2\n')

        shapes = self.read_shapes()

        self.assertEqual(1, len(shapes))
        self.assertEqual('cat', shapes[0][0])
        # height and width of the image are used to scale the relative values.
        self.assertEqual([(40, 20), (60, 20), (60, 30), (40, 30)], shapes[0][1])

    def test_missing_classes_file_is_not_fatal(self):
        with open(self.txt_path, 'w') as txt_file:
            txt_file.write('0 0.5 0.5 0.2 0.2\n')

        self.assertEqual([], self.read_shapes())

    def test_missing_annotation_file_is_not_fatal(self):
        self.write_classes('cat\n')

        self.assertEqual([], self.read_shapes())

    def test_non_finite_values_are_skipped(self):
        self.write_classes('cat\n')
        with open(self.txt_path, 'w') as txt_file:
            txt_file.write('0 nan 0.5 0.2 0.2\n'
                           '0 inf 0.5 0.2 0.2\n'
                           '0 1e309 0.5 0.2 0.2\n'
                           '0 0.5 0.5 0.2 0.2\n')

        shapes = self.read_shapes()

        self.assertEqual(1, len(shapes))
        self.assertEqual('cat', shapes[0][0])

    def test_blank_lines_and_trailing_spaces_are_ignored(self):
        self.write_classes('cat\ndog\n')
        with open(self.txt_path, 'w') as txt_file:
            txt_file.write('0 0.5 0.5 0.2 0.2\n\n1 0.3 0.4 0.1 0.1 \n')

        shapes = self.read_shapes()

        self.assertEqual(['cat', 'dog'], [shape[0] for shape in shapes])

    def test_values_separated_by_tabs_are_accepted(self):
        self.write_classes('cat\ndog\n')
        with open(self.txt_path, 'w') as txt_file:
            txt_file.write('0\t0.5\t0.5\t0.2\t0.2\n')

        self.assertEqual(1, len(self.read_shapes()))

    def test_class_index_out_of_range_is_skipped(self):
        self.write_classes('cat\ndog\n')
        with open(self.txt_path, 'w') as txt_file:
            txt_file.write('9 0.5 0.5 0.2 0.2\n0 0.5 0.5 0.2 0.2\n')

        shapes = self.read_shapes()

        self.assertEqual(['cat'], [shape[0] for shape in shapes])

    def test_non_numeric_class_index_is_skipped(self):
        self.write_classes('cat\ndog\n')
        with open(self.txt_path, 'w') as txt_file:
            txt_file.write('cat 0.5 0.5 0.2 0.2\n')

        self.assertEqual([], self.read_shapes())

    def test_incomplete_line_is_skipped(self):
        self.write_classes('cat\ndog\n')
        with open(self.txt_path, 'w') as txt_file:
            txt_file.write('0 0.5 0.5\n0 0.5 0.5 0.2 0.2\n')

        self.assertEqual(1, len(self.read_shapes()))

    def test_classes_file_is_read_as_utf8(self):
        self.write_classes(u'\u732b\u732b\n\u72d7\u72d7\n', encoding='utf-8-sig')
        with open(self.txt_path, 'w') as txt_file:
            txt_file.write('1 0.5 0.5 0.2 0.2\n')

        shapes = self.read_shapes()

        self.assertEqual(1, len(shapes))
        self.assertEqual(u'\u72d7\u72d7', shapes[0][0])

    def test_annotation_file_with_a_byte_order_mark_is_read(self):
        self.write_classes('cat\n')
        with codecs.open(self.txt_path, 'w', encoding='utf-8-sig') as txt_file:
            txt_file.write('0 0.5 0.5 0.2 0.2\n')

        self.assertEqual(1, len(self.read_shapes()))

    def test_classes_file_written_with_the_locale_encoding_is_read(self):
        self.write_classes(u'\u4e2d\u6587\ndog\n', encoding='cp936')

        self.assertEqual([u'\u4e2d\u6587', 'dog'], read_class_list(self.classes_path))

    def test_classes_file_with_invalid_encoding_is_not_fatal(self):
        with open(self.classes_path, 'wb') as classes_file:
            classes_file.write(b'\xff\xfe\x00\x00')

        self.assertEqual([], read_class_list(self.classes_path))

class TestYoloWriter(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix='labelImg-yolo-')
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)
        self.target = os.path.join(self.tmp_dir, 'img.txt')

    def test_class_list_is_saved_as_utf8(self):
        writer = YOLOWriter('folder', 'img', (50, 100, 3))
        writer.add_bnd_box(40, 20, 60, 30, u'\u732b\u732b', 0)
        writer.save(class_list=[], target_file=self.target)

        classes_path = os.path.join(self.tmp_dir, 'classes.txt')
        with codecs.open(classes_path, 'r', encoding='utf-8') as classes_file:
            self.assertEqual(u'\u732b\u732b\n', classes_file.read())

        self.assertEqual([u'\u732b\u732b'], read_class_list(classes_path))

    def test_saved_file_can_be_read_back(self):
        writer = YOLOWriter('folder', 'img', (50, 100, 3))
        writer.add_bnd_box(40, 20, 60, 30, 'cat', 0)
        writer.save(class_list=['cat'], target_file=self.target)

        reader = YoloReader(self.target, make_image(os.path.join(self.tmp_dir, 'img.png')))

        self.assertEqual(1, len(reader.get_shapes()))
        self.assertEqual('cat', reader.get_shapes()[0][0])

    def test_unknown_image_size_raises_a_value_error(self):
        writer = YOLOWriter('folder', 'img', [0, 0, 3])
        writer.add_bnd_box(1, 1, 10, 10, 'cat', 0)

        self.assertRaises(ValueError, writer.save, ['cat'], self.target)

if __name__ == '__main__':
    unittest.main()
