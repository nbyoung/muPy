import setuptools

from mupy import version

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name=version.NAME,
    version=str(version.VERSION),
    author="Norman Young",
    author_email="nbyoung@nbyoung.com",
    description="Multi-target application framework for MicroPython",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="development",
    url="https://github.com/nbyoung/muPy",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
    ],
    python_requires='>=3.6',
    install_requires=[
        'semantic_version',
        'PyYAML',
    ],
    extras_require={
        'docker': [ 'docker' ],
    },
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'mupy-host = mupy:main_host',
            'mupy-target = mupy:main_target',
            'mupy = mupy:main',
        ]
    },
)
