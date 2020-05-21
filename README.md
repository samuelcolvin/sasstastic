# sasstastic

[![CI](https://github.com/samuelcolvin/sasstastic/workflows/CI/badge.svg?event=push)](https://github.com/samuelcolvin/sasstastic/actions?query=event%3Apush+branch%3Amaster+workflow%3ACI)
[![Coverage](https://codecov.io/gh/samuelcolvin/sasstastic/branch/master/graph/badge.svg)](https://codecov.io/gh/samuelcolvin/sasstastic)
[![pypi](https://img.shields.io/pypi/v/sasstastic.svg)](https://pypi.python.org/pypi/sasstastic)
[![versions](https://img.shields.io/pypi/pyversions/sasstastic.svg)](https://github.com/samuelcolvin/sasstastic)
[![license](https://img.shields.io/github/license/samuelcolvin/sasstastic.svg)](https://github.com/samuelcolvin/sasstastic/blob/master/LICENSE)

**Fantastic SASS and SCSS compilation for python**

## Installation

```bash
pip install sasstastic
```

run

```bash
sasstastic --help
```

To check sasstastic is install and get help info.

## Usage

Define a config file `sasstastic.yml`:

```yaml
download:
  # downloaded files will be saved in this directory
  dir: styles/.libs
  sources:
    # download a font css file from google fonts and save it to goog-fonts.css
    - url: >
       https://fonts.googleapis.com/css?
       family=Merriweather:400,400i,700,700i|Titillium+Web|Ubuntu+Mono&display=swap
      to: google-fonts.css

    # download a style sheet from select2, this will be saved to "select2.css" as
    # the name can be inferred from the url
    - url: 'https://raw.githubusercontent.com/select2/select2/4.0.13/dist/css/select2.css'

    # download the full bootstrap 4 bundle and extract the scss files to the bootstrap/ directory
    - url: https://github.com/twbs/bootstrap/archive/v4.4.1.zip
      extract:
        'bootstrap-4.4.1/scss/(.+)$': bootstrap/


# SCSS and SASS files will be build from this directory
build_dir: styles/
# and saved to this directory
output_dir: css/
# the output directory "css/" will be deleted before all builds
wipe_output_dir: true
```

Then run `sasstastic` to build your sass files.

note:
* if you `sasstastic.yml` file isn't in the current working directory you can pass the path to that file
  as an argument to sasstastic, e.g. `sasstastic path/to/sasstastic.yml` or just `sasstastic path/to/`
* by default the paths defined in `sasstastic.yml`: `download.dir`, `build_dir` and `output_dir` are 
  **relative to the the `sasstastic.yml` file
* you can override the output directory `ouput_dir` using the `-o` argument to the CLI, see `sasstastic --help`
  for more info
* sasstastic can build in "development" or "production" mode:
  * in **development** mode css is not compressed, a map file is created and all files from `build_dir` and 
    `download.dir` are copied into `output_dir` so map files work correctly
  * in **production** mode css is compressed, no other files are added to `output_dir`
