import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('display-requirements.txt') as f:
    display_requirements = f.read().splitlines()

setuptools.setup(
    name="ladybug-radiance",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    author="Ladybug Tools",
    author_email="info@ladybug.tools",
    description='Radiance extension for Ladybug, used for all radiation studies '
    'and graphics.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ladybug-tools/ladybug-radiance",
    packages=setuptools.find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        'display': display_requirements
    },
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent"
    ],
    license="AGPL-3.0"
)
