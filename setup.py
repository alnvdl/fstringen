import setuptools

setuptools.setup(
    name="fstringen",
    version="0.0.3",
    author="Allan Vidal",
    description="A text generator based on f-strings",
    url="https://github.com/alnvdl/fstringen",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: Apache Software License"
    ],
    python_requires=">=3.6"
)
