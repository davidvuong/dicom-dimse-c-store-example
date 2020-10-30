# dicom-dimse-c-store-example

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)

**Welcome to dicom-dimse-c-store-example!**

This is a sample project which demonstrates how to quickly build a DIMSE C-STORE AE. It includes both an SCU and an SCP written using `pynetdicom` and `pydicom` libraries. Datasets sent through `C-STORE` operations are parsed and logged to console.

You can read more about how this works [here](https://www.voltron.studio/article/build-a-dicom-dimse-c-store-service-with-python).

## Getting Started

Clone the repository:

```bash
git clone git@github.com:voltronstudio/dicom-dimse-c-store-example
```

Install project dependencies:

```bash
poetry install
```

Start the SCP AE:

```bash
poetry run python ./dicom-dimse-c-store-example/scp.py
```

Start the SCU AE and send a C-STORE operation using a DICOM file stored locally:

```bash
poetry run python ./dicom-dimse-c-store-example/scu.py <path_to_dicoms>
```
