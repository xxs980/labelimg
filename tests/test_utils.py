import os
import sys
import unittest
from libs.utils import Struct, new_action, new_icon, add_actions, format_shortcut, generate_color_by_text, natural_sort
from libs.utils import LABEL_COLORS

class TestUtils(unittest.TestCase):

    def test_generateColorByGivingUniceText_noError(self):
        res = generate_color_by_text(u'\u958B\u555F\u76EE\u9304')
        self.assertTrue(res.green() >= 0)
        self.assertTrue(res.red() >= 0)
        self.assertTrue(res.blue() >= 0)

    def test_a_label_always_gets_the_same_color(self):
        self.assertEqual(generate_color_by_text('cat').name(),
                         generate_color_by_text('cat').name())
        self.assertEqual(255, generate_color_by_text('cat').alpha())

    def test_every_class_of_the_palette_gets_its_own_color(self):
        names = [generate_color_by_text('label', index=index).name()
                 for index in range(len(LABEL_COLORS))]

        self.assertEqual(len(LABEL_COLORS), len(set(names)))

    def test_no_label_color_is_pale(self):
        def channel(value):
            value = value / 255.0
            if value <= 0.03928:
                return value / 12.92
            return ((value + 0.055) / 1.055) ** 2.4

        for red, green, blue in LABEL_COLORS:
            luminance = (0.2126 * channel(red) + 0.7152 * channel(green)
                         + 0.0722 * channel(blue))
            self.assertLessEqual(luminance, 0.30, (red, green, blue))

    def test_nautalSort_noError(self):
        l1 = ['f1', 'f11', 'f3']
        expected_l1 = ['f1', 'f3', 'f11']
        natural_sort(l1)
        for idx, val in enumerate(l1):
            self.assertTrue(val == expected_l1[idx])

if __name__ == '__main__':
    unittest.main()
