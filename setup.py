try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import sys
sys.path.insert(0, '.')
import version


setup(name='clutter-webcam-viewer',
      version=version.getVersion(),
      author='Christian Fobel',
      author_email='christian@fobel.net',
      url='https://github.com/cfobel/clutter-webcam-viewer',
      license='LGPL-3.0',
      install_requires=['pygtk3-helpers>=0.2'],
      packages=['clutter_webcam_viewer'])
