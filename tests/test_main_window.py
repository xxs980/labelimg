import os
import shutil
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# The application keeps its settings in the home folder. Point it to a scratch
# directory so that a test can neither pick up nor overwrite a real session.
TEST_HOME = tempfile.mkdtemp(prefix='labelImg-home-')
os.environ['HOME'] = TEST_HOME
os.environ['USERPROFILE'] = TEST_HOME

from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication, QMessageBox

import mlabelImg

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASS_FILE = os.path.join(REPO_DIR, 'data', 'predefined_classes.txt')

def save_image(folder, name):
    image = QImage(20, 10, QImage.Format_RGB32)
    image.fill(0xFFFFFFFF)
    image.save(os.path.join(folder, name))

class MainWindowTestCase(unittest.TestCase):

    app = None

    @classmethod
    def setUpClass(cls):
        if cls.app is None:
            cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # Everything lives in a scratch tree. An image outside of the directory
        # under test makes it obvious when another folder gets scanned instead.
        self.base_dir = tempfile.mkdtemp(prefix='labelImg-scratch-')
        self.addCleanup(shutil.rmtree, self.base_dir, True)
        self.dir_path = os.path.join(self.base_dir, 'images')
        os.makedirs(self.dir_path)
        save_image(self.base_dir, 'stray.png')

        # Never block on a modal dialog, the answer is controlled per test.
        self.reply = QMessageBox.Yes
        for name in ('question', 'information', 'warning', 'critical'):
            original = getattr(QMessageBox, name)
            self.addCleanup(setattr, QMessageBox, name, original)
            setattr(QMessageBox, name, self._stub_dialog(name))

    def _stub_dialog(self, name):
        def dialog(*_args, **_kwargs):
            if name == 'question':
                return self.reply
            return QMessageBox.Ok
        return staticmethod(dialog)

    def make_images(self, count):
        names = ['img_%d.png' % index for index in range(1, count + 1)]
        for name in names:
            save_image(self.dir_path, name)
        return names

    def open_dir(self, save_dir=None):
        return mlabelImg.MainWindow(self.dir_path, CLASS_FILE, save_dir or self.dir_path)

    def given_current_image(self, window, name):
        file_path = os.path.join(self.dir_path, name)
        window.load_file(file_path)
        window.cur_img_idx = window.m_img_list.index(file_path)
        return window

    def names(self, window):
        return [os.path.basename(path) for path in window.m_img_list]

    def given_file(self, folder, name, content):
        path = os.path.join(folder, name)
        with open(path, 'w') as handle:
            handle.write(content)
        return path

    def current_name(self, window):
        return os.path.basename(window.file_path) if window.file_path else None

    def test_opening_a_directory_loads_that_directory(self):
        names = self.make_images(3)

        window = self.open_dir()

        self.assertEqual(names, self.names(window))
        self.assertEqual(3, window.img_count)
        self.assertEqual('img_1.png', self.current_name(window))

    def test_opening_a_directory_without_a_class_file_works(self):
        self.make_images(1)

        window = mlabelImg.MainWindow(self.dir_path, None, None)

        self.assertEqual(1, window.img_count)

    def test_deleting_an_image_shows_the_next_one(self):
        self.make_images(3)
        window = self.given_current_image(self.open_dir(), 'img_2.png')

        window.delete_image()

        self.assertEqual(['img_1.png', 'img_3.png'], self.names(window))
        self.assertEqual('img_3.png', self.current_name(window))
        self.assertEqual(1, window.cur_img_idx)
        self.assertEqual(2, window.img_count)

    def test_deleting_the_last_image_shows_the_new_last_one(self):
        self.make_images(3)
        window = self.given_current_image(self.open_dir(), 'img_3.png')

        window.delete_image()

        self.assertEqual('img_2.png', self.current_name(window))
        self.assertEqual(1, window.cur_img_idx)

    def test_deleting_the_only_image_empties_the_view(self):
        self.make_images(1)
        window = self.given_current_image(self.open_dir(), 'img_1.png')

        window.delete_image()

        self.assertEqual([], self.names(window))
        self.assertEqual(0, window.img_count)
        self.assertIsNone(window.file_path)
        self.assertEqual(0, window.cur_img_idx)

    def test_deleting_an_image_without_annotations_works(self):
        self.make_images(2)
        window = self.given_current_image(self.open_dir(), 'img_1.png')

        window.delete_image()

        self.assertEqual(['img_2.png'], self.names(window))

    def test_deleting_an_image_removes_all_of_its_annotations(self):
        self.make_images(2)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        annotations = [self.given_file(self.dir_path, 'img_1.' + extension, content) for extension, content in
                       (('xml', '<annotation/>\n'), ('txt', '0 0.5 0.5 0.2 0.2\n'), ('json', '[]\n'))]
        kept = [self.given_file(self.dir_path, 'classes.txt', 'cat\ndog\n'),
                self.given_file(self.dir_path, 'img_2.xml', '<annotation/>\n')]

        window.delete_image()

        for annotation in annotations:
            self.assertFalse(os.path.exists(annotation), '%s is left behind' % annotation)
        for kept_file in kept:
            self.assertTrue(os.path.isfile(kept_file), '%s was deleted' % kept_file)

    def test_deleting_an_image_removes_annotations_stored_elsewhere(self):
        save_dir = os.path.join(self.base_dir, 'annotations')
        os.makedirs(save_dir)
        self.make_images(2)
        window = self.given_current_image(self.open_dir(save_dir), 'img_1.png')
        annotation = self.given_file(save_dir, 'img_1.xml', '<annotation/>\n')

        window.delete_image()

        self.assertFalse(os.path.exists(annotation))
        self.assertFalse(os.path.exists(os.path.join(self.dir_path, 'img_1.png')))

    def test_deleting_is_cancelled_when_answered_no(self):
        self.make_images(2)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        self.reply = QMessageBox.No

        window.delete_image()

        self.assertEqual('img_1.png', self.current_name(window))
        self.assertTrue(os.path.isfile(os.path.join(self.dir_path, 'img_1.png')))
        self.assertEqual(2, window.img_count)

    def test_deleting_without_an_open_image_works(self):
        self.make_images(1)
        window = self.open_dir()
        window.reset_state()

        window.delete_image()

        self.assertEqual(1, window.img_count)

    def test_copying_bounding_boxes_without_an_open_image_works(self):
        self.make_images(2)
        window = self.open_dir()
        window.reset_state()

        window.copy_previous_bounding_boxes()

        self.assertIsNone(window.file_path)

    def test_copying_bounding_boxes_of_an_unlisted_file_works(self):
        self.make_images(2)
        window = self.open_dir()
        window.file_path = os.path.join(TEST_HOME, 'not_scanned.png')

        window.copy_previous_bounding_boxes()

        self.assertEqual(2, window.img_count)

    def test_loading_an_annotation_file_is_rejected(self):
        names = self.make_images(2)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        annotation = self.given_file(self.dir_path, 'img_1.xml', '<annotation/>\n')

        self.assertFalse(window.load_file(annotation))
        self.assertEqual(names, self.names(window))
        self.assertEqual(2, window.img_count)

    def test_loading_an_empty_path_is_rejected(self):
        self.make_images(1)
        window = self.open_dir()

        self.assertFalse(window.load_file(''))

    def test_navigation_after_loading_an_image_outside_the_directory(self):
        names = self.make_images(2)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        outside = os.path.join(self.base_dir, 'outside.png')
        save_image(self.base_dir, 'outside.png')

        self.assertTrue(window.load_file(outside))
        self.assertEqual(names, self.names(window))

        window.open_next_image()

        self.assertEqual('img_2.png', self.current_name(window))

    def test_zooming_after_closing_the_file_works(self):
        self.make_images(1)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        # Flush the initial directory import before closing the file.
        self.app.processEvents()

        window.close_file()
        window.adjust_scale()
        window.set_fit_window()
        window.set_fit_width()
        window.resize(640, 480)
        self.app.processEvents()

        self.assertIsNone(window.file_path)

    def test_double_clicking_an_unknown_or_missing_item_works(self):
        self.make_images(2)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        unknown = mlabelImg.QListWidgetItem(os.path.join(self.base_dir, 'unknown.png'))

        window.file_item_double_clicked(None)
        window.file_item_double_clicked(unknown)

        self.assertEqual('img_1.png', self.current_name(window))

    def test_copying_or_adding_without_a_selected_shape_works(self):
        self.make_images(1)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        window.canvas.de_select_shape()

        window.copy_selected_shape()
        window.add_label(None)

        self.assertEqual(0, window.label_list.count())

    def test_unreadable_or_invalid_class_file_does_not_crash(self):
        self.make_images(1)
        invalid_class_file = os.path.join(self.base_dir, 'classes.txt')
        with open(invalid_class_file, 'wb') as class_file:
            class_file.write(b'\xff\xfe\x00\x00')

        window = mlabelImg.MainWindow(self.dir_path, invalid_class_file, self.dir_path)
        directory_window = mlabelImg.MainWindow(self.dir_path, self.base_dir, self.dir_path)

        self.assertEqual([], window.label_hist)
        self.assertEqual([], directory_window.label_hist)

    def test_deleting_a_selection_after_navigating_does_not_crash(self):
        self.make_images(2)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        shape = mlabelImg.Shape(label='cat')
        for point in ((1, 1), (5, 1), (5, 5), (1, 5)):
            shape.add_point(mlabelImg.QPointF(*point))
        shape.close()
        window.canvas.load_shapes([shape])
        window.add_label(shape)
        shape.selected = True
        window.canvas.selected_shape = shape
        window.shape_selection_changed(True)

        window.load_file(os.path.join(self.dir_path, 'img_2.png'))
        window.delete_selected_shape()

        self.assertIsNone(window.canvas.selected_shape)
        self.assertEqual(0, window.label_list.count())

    def test_saving_into_an_unwritable_path_reports_an_error(self):
        self.make_images(1)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        os.makedirs(os.path.join(self.dir_path, 'img_1.xml'))

        window.save_file()

        self.assertTrue(os.path.isdir(os.path.join(self.dir_path, 'img_1.xml')))

    def test_saving_after_closing_the_file_works(self):
        self.make_images(1)
        window = mlabelImg.MainWindow(self.dir_path, CLASS_FILE, None)
        self.app.processEvents()
        window.close_file()

        window.save_file()
        window.save_file_as()

        self.assertIsNone(window.file_path)

    def test_renaming_the_selected_label_updates_the_combo_box(self):
        self.make_images(1)
        window = self.given_current_image(self.open_dir(), 'img_1.png')
        shape = mlabelImg.Shape(label='cat')
        for point in ((1, 1), (5, 1), (5, 5), (1, 5)):
            shape.add_point(mlabelImg.QPointF(*point))
        shape.close()
        window.canvas.load_shapes([shape])
        window.add_label(shape)
        window.combo_box.cb.setCurrentIndex(window.combo_box.cb.findText('cat'))

        window.label_list.item(0).setText('dog')
        window.update_combo_box()

        self.assertGreaterEqual(window.combo_box.cb.findText('dog'), 0)

if __name__ == '__main__':
    unittest.main()
