import codecs
import os
import shutil
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5.QtGui import QImage

from libs.labelFile import LabelFile
from libs.labelFile import LabelFileError
from libs.pascal_voc_io import PascalVocReader
from libs.pascal_voc_io import PascalVocWriter

def shape(label, points, difficult=0):
    return {'label': label, 'points': points, 'difficult': difficult}

class LabelFileTestCase(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix='labelImg-labelfile-')
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)
        self.image_path = os.path.join(self.tmp_dir, 'img.png')
        self.image = QImage(100, 50, QImage.Format_RGB32)
        self.image.fill(0xFFFFFFFF)
        self.image.save(self.image_path)

class TestPointConversion(LabelFileTestCase):

    def test_empty_points_raise_a_value_error(self):
        self.assertRaises(ValueError, LabelFile.convert_points_to_bnd_box, [])

class TestLabelFileWriters(LabelFileTestCase):

    def test_pascal_save_skips_shapes_without_points(self):
        target = os.path.join(self.tmp_dir, 'img.xml')

        LabelFile().save_pascal_voc_format(
            target,
            [shape('empty', []), shape('cat', [(10, 10), (30, 20)])],
            self.image_path, self.image)

        shapes = PascalVocReader(target).get_shapes()
        self.assertEqual(['cat'], [each_shape[0] for each_shape in shapes])

    def test_yolo_save_skips_shapes_without_points(self):
        target = os.path.join(self.tmp_dir, 'img.txt')

        LabelFile().save_yolo_format(
            target,
            [shape('empty', []), shape('cat', [(40, 20), (60, 30)])],
            self.image_path, self.image, ['cat'])

        with codecs.open(target, 'r', encoding='utf-8') as target_file:
            lines = target_file.read().splitlines()
        self.assertEqual(['0 0.500000 0.500000 0.200000 0.200000'], lines)

    def test_yolo_save_without_a_valid_image_raises_label_file_error(self):
        target = os.path.join(self.tmp_dir, 'img.txt')

        self.assertRaises(LabelFileError, LabelFile().save_yolo_format,
                          target, [], os.path.join(self.tmp_dir, 'missing.png'), None, ['cat'])

class TestPascalVocWriter(LabelFileTestCase):

    def test_saving_an_incomplete_annotation_raises_a_value_error(self):
        target = os.path.join(self.tmp_dir, 'incomplete.xml')
        writer = PascalVocWriter('folder', None, (50, 100, 3))

        self.assertRaises(ValueError, writer.save, target)
        self.assertFalse(os.path.exists(target))

if __name__ == '__main__':
    unittest.main()
