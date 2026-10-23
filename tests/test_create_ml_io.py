import json
import os
import shutil
import tempfile
import unittest

from libs.create_ml_io import CreateMLReader
from libs.create_ml_io import CreateMLWriter

def rect(label, x_min, y_min, x_max, y_max):
    return {'label': label,
            'points': ((x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max))}

class CreateMLTestCase(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix='labelImg-createml-')
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)
        self.output_file = os.path.join(self.tmp_dir, 'Annotation.json')

    def writer(self, shapes):
        return CreateMLWriter('folder', 'img.png', (50, 100, 3), shapes, self.output_file)

    def read_output(self):
        with open(self.output_file, 'r') as output_file:
            return json.load(output_file)

    def given_content(self, content):
        with open(self.output_file, 'w') as output_file:
            output_file.write(content)

class TestCreateMLWriter(CreateMLTestCase):

    def test_creates_the_annotation_file(self):
        self.writer([rect('cat', 40, 20, 60, 30)]).write()

        entries = self.read_output()

        self.assertEqual(1, len(entries))
        self.assertEqual('img.png', entries[0]['image'])
        self.assertEqual('cat', entries[0]['annotations'][0]['label'])

    def test_keeps_the_annotations_of_the_other_images(self):
        other = {'image': 'other.png', 'annotations': []}
        self.given_content(json.dumps([other]))

        self.writer([rect('cat', 40, 20, 60, 30)]).write()

        entries = self.read_output()
        self.assertEqual(['other.png', 'img.png'], [entry['image'] for entry in entries])

    def test_broken_annotation_file_is_backed_up_instead_of_raising(self):
        self.given_content('{"image": "img.png", broken')

        self.writer([rect('cat', 40, 20, 60, 30)]).write()

        self.assertEqual(['img.png'], [entry['image'] for entry in self.read_output()])
        self.assertTrue(os.path.isfile(self.output_file + '.bak'))

    def test_annotation_file_of_unexpected_layout_is_not_fatal(self):
        self.given_content(json.dumps({'info': {'year': 2020}}))

        self.writer([rect('cat', 40, 20, 60, 30)]).write()

        self.assertEqual(1, len(self.read_output()))

    def test_entries_without_the_image_key_are_ignored(self):
        self.given_content(json.dumps([{'filename': 'img.png', 'regions': []}]))

        self.writer([rect('cat', 40, 20, 60, 30)]).write()

        entries = self.read_output()
        self.assertEqual(2, len(entries))
        self.assertEqual('img.png', entries[1]['image'])

    def test_line_shape_is_written_as_its_bounding_box(self):
        self.writer([{'label': 'line', 'points': ((10, 20), (30, 40))}]).write()

        annotation = self.read_output()[0]['annotations'][0]

        self.assertEqual({'x': 20, 'y': 30, 'width': 20, 'height': 20},
                         annotation['coordinates'])

    def test_shape_without_points_is_skipped(self):
        self.writer([{'label': 'empty', 'points': ()},
                     rect('cat', 40, 20, 60, 30)]).write()

        annotations = self.read_output()[0]['annotations']
        self.assertEqual(['cat'], [annotation['label'] for annotation in annotations])

class TestCreateMLReader(CreateMLTestCase):

    def read_shapes(self):
        return CreateMLReader(self.output_file, os.path.join(self.tmp_dir, 'img.png')).get_shapes()

    def test_reads_the_own_format(self):
        self.writer([rect('cat', 40, 20, 60, 30)]).write()

        shapes = self.read_shapes()

        self.assertEqual(1, len(shapes))
        self.assertEqual('cat', shapes[0][0])
        self.assertEqual([(40, 20), (60, 20), (60, 30), (40, 30)], shapes[0][1])

    def test_only_reads_the_requested_image(self):
        self.given_content(json.dumps([{'image': 'other.png',
                                        'annotations': [{'label': 'cat',
                                                         'coordinates': {'x': 50, 'y': 25,
                                                                         'width': 20, 'height': 10}}]}]))

        self.assertEqual([], self.read_shapes())

    def test_broken_json_is_not_fatal(self):
        self.given_content('[{,')

        self.assertEqual([], self.read_shapes())

    def test_json_of_unexpected_layout_is_not_fatal(self):
        self.given_content(json.dumps({'info': {'year': 2020}}))

        self.assertEqual([], self.read_shapes())

    def test_non_finite_coordinates_are_skipped(self):
        self.given_content(json.dumps([{
            'image': 'img.png',
            'annotations': [
                {'label': 'bad', 'coordinates': {'x': float('nan'), 'y': 10,
                                                 'width': 5, 'height': 5}},
                {'label': 'cat', 'coordinates': {'x': 50, 'y': 25,
                                                 'width': 20, 'height': 10}},
            ],
        }]))

        shapes = self.read_shapes()

        self.assertEqual(['cat'], [shape[0] for shape in shapes])

    def test_incomplete_annotation_is_not_fatal(self):
        self.given_content(json.dumps([{'image': 'img.png', 'annotations': [{'label': 'cat'}]}]))

        self.assertEqual([], self.read_shapes())

if __name__ == '__main__':
    unittest.main()
