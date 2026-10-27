from math import sqrt
from libs.ustr import ustr
import hashlib
import re
import sys

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    QT5 = True
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
    QT5 = False


def new_icon(icon):
    return QIcon(':/' + icon)


def new_button(text, icon=None, slot=None):
    b = QPushButton(text)
    if icon is not None:
        b.setIcon(new_icon(icon))
    if slot is not None:
        b.clicked.connect(slot)
    return b


def new_action(parent, text, slot=None, shortcut=None, icon=None,
               tip=None, checkable=False, enabled=True):
    """Create a new action and assign callbacks, shortcuts, etc."""
    a = QAction(text, parent)
    if icon is not None:
        a.setIcon(new_icon(icon))
    if shortcut is not None:
        if isinstance(shortcut, (list, tuple)):
            a.setShortcuts(shortcut)
        else:
            a.setShortcut(shortcut)
    if tip is not None:
        a.setToolTip(tip)
        a.setStatusTip(tip)
    if slot is not None:
        a.triggered.connect(slot)
    if checkable:
        a.setCheckable(True)
    a.setEnabled(enabled)
    return a


def add_actions(widget, actions):
    for action in actions:
        if action is None:
            widget.addSeparator()
        elif isinstance(action, QMenu):
            widget.addMenu(action)
        else:
            widget.addAction(action)


def label_validator():
    return QRegExpValidator(QRegExp(r'^[^ \t].+'), None)


class Struct(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def distance(p):
    return sqrt(p.x() * p.x() + p.y() * p.y())


def format_shortcut(text):
    mod, key = text.split('+', 1)
    return '<b>%s</b>+<b>%s</b>' % (mod, key)


# A qualitative palette of saturated colors. The entries come from the
# ColorBrewer and Tableau palettes, which are widely used because their colors
# are easy to tell apart and stay readable on light as well as on dark images.
# Every color has a luminance below 0.30, so no box washes out on a white photo.
LABEL_COLORS = [
    (0x4E, 0x79, 0xA7),  # blue
    (0xD9, 0x5F, 0x02),  # dark orange
    (0x59, 0xA1, 0x4F),  # green
    (0xE7, 0x29, 0x8A),  # magenta
    (0xB8, 0x86, 0x0B),  # dark goldenrod
    (0x1B, 0x9E, 0x77),  # dark teal
    (0xE1, 0x57, 0x59),  # red
    (0x75, 0x70, 0xB3),  # lavender blue
    (0x5A, 0x91, 0x19),  # olive green
    (0x0E, 0x9A, 0xA8),  # cyan
    (0xC2, 0x4E, 0x9A),  # pink
    (0x9C, 0x75, 0x5F),  # brown
    (0x3F, 0x6F, 0xA8),  # navy
    (0xD9, 0x7A, 0x1A),  # orange
    (0x4E, 0x9E, 0x99),  # teal
    (0xC0, 0x39, 0x2B),  # dark red
    (0xB0, 0x7A, 0xA1),  # purple
    (0x66, 0x66, 0x66),  # gray
]


def generate_color_by_text(text, alpha=255, index=None):
    """Return the color of a label.

    The optional index is the position of the class in the class list. It gives
    each class of a dataset a different color. Without it the name of the label
    selects the color, so a label always keeps the same one.
    """
    if index is None:
        digest = hashlib.sha256(ustr(text).encode('utf-8')).hexdigest()
        index = int(digest, 16)
    red, green, blue = LABEL_COLORS[index % len(LABEL_COLORS)]
    return QColor(red, green, blue, alpha)


def have_qstring():
    """p3/qt5 get rid of QString wrapper as py3 has native unicode str type"""
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))


def util_qt_strlistclass():
    return QStringList if have_qstring() else list


def natural_sort(list, key=lambda s:s):
    """
    Sort the list into natural alphanumeric order.
    """
    def get_alphanum_key_func(key):
        convert = lambda text: int(text) if text.isdigit() else text
        return lambda s: [convert(c) for c in re.split('([0-9]+)', key(s))]
    sort_key = get_alphanum_key_func(key)
    list.sort(key=sort_key)


# QT4 has a trimmed method, in QT5 this is called strip
if QT5:
    def trimmed(text):
        return text.strip()
else:
    def trimmed(text):
        return text.trimmed()
