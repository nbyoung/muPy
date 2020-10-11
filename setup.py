import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name="mupy",
    version="0.0.1",
    author="Norman Young",
    author_email="nbyoung@nbyoung.com",
    description="Multi-target application framework for MicroPython",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nbyoung/muPy",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
    ],
    python_requires='>=3.3',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'mupy-host = mupy:main_host',
            'mupy-target = mupy:main_target',
            'mupy = mupy:main',
        ]
    },
)
