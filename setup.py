import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'requirements.txt')) as f:
    reqs = f.read().split()

with open(os.path.join(here, 'README.md')) as f:
    readme = f.read()

def get_version(module_path):
    with open(module_path) as f:
        for line in f.readlines():
            if line.startswith('__version__'):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
        else:
            raise RuntimeError("Unable to find version string.")

setup(name='xword_dl',
        version=get_version(os.path.join(here, 'xword_dl.py')),
        description='a download tool for online crossword puzzles',
        long_description=readme,
        long_description_content_type='text/markdown',
        url='https://github.com/thisisparker/xword-dl',
        author='Parker Higgins',
        author_email='parker@parkerhiggins.net',
        py_modules=['xword_dl'],
        packages=[''],
        package_data={'':['']},
        python_requires='>=3.4',
        install_requires=reqs,
        entry_points={
            'console_scripts': [
                'xword-dl=xword_dl:main',
            ],
        },
    )

