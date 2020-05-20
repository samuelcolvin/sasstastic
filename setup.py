from importlib.machinery import SourceFileLoader
from pathlib import Path

from setuptools import setup

description = 'Fantastic SASS and SCSS compilation for python'
THIS_DIR = Path(__file__).resolve().parent
try:
    long_description = THIS_DIR.joinpath('README.md').read_text()
except FileNotFoundError:
    long_description = description

# avoid loading the package before requirements are installed:
version = SourceFileLoader('version', 'sasstastic/version.py').load_module()

setup(
    name='sasstastic-web',
    version=str(version.VERSION),
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Operating System :: POSIX :: Linux',
        'Environment :: MacOS X',
        'Topic :: Internet',
    ],
    author='Samuel Colvin',
    author_email='s@muelcolvin.com',
    url='https://github.com/samuelcolvin/sasstastic',
    license='MIT',
    packages=['sasstastic'],
    package_data={'sasstastic': ['py.typed']},
    entry_points="""
        [console_scripts]
        sasstastic=sasstastic.__main__:cli
    """,
    python_requires='>=3.6',
    zip_safe=True,
    install_requires=[
        'libsass>=0.20.0',
        'httpx>=0.12.1',
        'pydantic>=1.5',
        'typer>=0.1.0',
        'watchgod>=0.6',
    ],
)
