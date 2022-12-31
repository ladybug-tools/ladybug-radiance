
![Ladybug](http://www.ladybug.tools/assets/img/ladybug.png)

[![Build Status](https://github.com/ladybug-tools/ladybug-radiance/workflows/CI/badge.svg)](https://github.com/ladybug-tools/ladybug-radiance/actions)

[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/) [![Python 2.7](https://img.shields.io/badge/python-2.7-green.svg)](https://www.python.org/downloads/release/python-270/) [![IronPython](https://img.shields.io/badge/ironpython-2.7-red.svg)](https://github.com/IronLanguages/ironpython2/releases/tag/ipy-2.7.8/)

# ladybug-radiance

Ladybug-radiance is a Python library that adds Radiance-related functionalities to
[ladybug-core](https://github.com/ladybug-tools/ladybug/).

## [API Documentation](https://www.ladybug.tools/ladybug-radiance/docs/)

## Installation

`pip install ladybug-radiance`

## QuickStart

```python
import ladybug_radiance

```

## Local Development

1. Clone this repo locally
```console
git clone git@github.com:ladybug-tools/ladybug-radiance

# or

git clone https://github.com/ladybug-tools/ladybug-radiance
```
2. Install dependencies:
```console
cd ladybug-radiance
pip install -r dev-requirements.txt
pip install -r requirements.txt
```

3. Run Tests:
```console
python -m pytest tests/
```

4. Generate Documentation:
```console
sphinx-apidoc -f -e -d 4 -o ./docs ./ladybug_radiance
sphinx-build -b html ./docs ./docs/_build/docs
```
