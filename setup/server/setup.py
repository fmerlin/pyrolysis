import os

import pyrolysis.server
from setuptools import setup, find_packages

this_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_dir, 'README.rst'), 'r') as f:
    long_description = f.read()

# More information on properties: https://packaging.python.org/distributing
setup(name='pyrolysis-server',
      version=pyrolysis.server.__version__,
      author='Francois Merlin',
      author_email='fmerlin@gmail.com',
      url="https://github.com/fmerlin/pyrolysis.git",
      description="Access REST APIs from python using functions",
      long_description=long_description,
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers"
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6"
      ],
      keywords=[
          'openapi',
          'swagger',
          'rest',
          'service'
      ],
      packages=find_packages(exclude=['tests', 'fixture']),
      tests_require=[
          # Used to run tests
          'nose',
      ],
      install_requires=[
          # Used to parse all date-time formats in a easy way
          'python-dateutil',
          'flask',
          'flask_swagger',
          'jwt',
          'marshmallow_jsonschema',
      ],
      platforms=[
          'Windows',
          'Linux'
      ]
      )
