#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="document-search-backend",
    version="0.1.0",
    description="Backend for document search application",
    packages=find_packages(),
    install_requires=[
        "flask==2.3.3",
        "flask-cors==4.0.0",
        "pandas==2.0.3",
        "pytesseract==0.3.10",
        "pillow==10.0.1",
        "PyPDF2==3.0.1",
        "openpyxl==3.1.2",
        "werkzeug==2.3.7",
    ],
    python_requires=">=3.8",
)