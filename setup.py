import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'requirements.txt')) as f:
    reqs = f.read().split()

with open(os.path.join(here, 'README.md')) as f:
    readme = f.read()

with open(os.path.join(here, 'version')) as f:
    version= f.read().strip()

setup(name='xword_dl',
        version=version,
        description='a download tool for online crossword puzzles',
        long_description=readme,
        long_description_content_type='text/markdown',
        url='https://github.com/thisisparker/xword-dl',
        author='Parker Higgins',
        author_email='parker@parkerhiggins.net',
        py_modules=['xword_dl'],
        python_requires='>=3.4',
        install_requires=reqs,
        entry_points={
            'console_scripts': [
                'xword-dl=xword_dl:main',
            ],
        },
    )

