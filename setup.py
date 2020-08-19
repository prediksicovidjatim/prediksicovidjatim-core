import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name='prediksicovidjatim',  
    version='0.15',
    author="Prediksi Covid Jatim",
    author_email="prediksicovidjatim@gmail.com",
    description="Core library of prediksicovidjatim",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/prediksicovidjatim/prediksicovidjatim-core",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)