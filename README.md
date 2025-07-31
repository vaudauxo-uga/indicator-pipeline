# SpO2 Indicator Extraction Pipeline

## Overview

This pipeline aims to compute clinical indicators based on the SpO2 signal extracted from polysomnography recordings (EDF format with optional annotations in `.csv`, `.txt`, or `.rtf`).  
The processing workflow follows these main steps:

1. **EDF Conversion**: Raw polysomnography files are first converted to the *Sleeplab* format using a dedicated tool. Converted files are stored both on the network storage and locally.
2. **Manual Indicator Calculation**: Indicators are computed manually using the [ABOSA software](https://zenodo.org/records/6962129).
3. **Integration into MARS Database**: The final step consists in parsing the ABOSA output files (Excel format) and injecting the computed indicators into the MARS database (oximetry-specific tables) through a POST method sending `json` payloads.

## Intended Use

This pipeline is designed to be executed on a Windows environment, typically either a dedicated physical machine or a virtual machine (VM) equipped with the required tools.

## Input Data

- Raw polysomnography recordings in EDF format
- Annotation files in `.csv`, `.txt`, or `.rtf`
- ABOSA-generated Excel files (`ParameterValues_...` folders)

## Output Data

- Parsed JSON files containing indicators ready for MARS database insertion
- Log files for traceability and reproducibility

## Installation and Setup

### Cloning the Repository

The project is version-controlled with Git and should be cloned locally before use:

```bash
git clone <REPO_URL>
cd indicator-pipeline
```

### Dependency Installation
Dependencies are listed in the `pyproject.toml` file. It is recommended to use a virtual environment (e.g., venv):

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install .
```

### Environment Configuration with .env
The pipeline uses a .env file to store environment-specific and sensitive variables, such as SFTP credentials and database connection parameters.

Example .env file:
```bash
SFTP_HOST=my.server.com
SFTP_USER=user
SFTP_KEY_PATH=pathtosshkey
SFTP_PASSWORD=password
SFTP_PORT=sftpport
```

Location:

The .env file must be placed at the root of the project, next to pyproject.toml.

It is automatically loaded using the `python-dotenv` library in the appropriate modules.

**Do not version this file**: it is excluded by .gitignore.

## Main Script

### Execution
To execute the pipeline manually:

```bash
run-pipeline --years
```

### Arguments
`--years`: Required. One or more years to process, each corresponding to a folder name on the SFTP server. Multiple years can be provided as space-separated values (e.g., --years 2024 2025).


## Additional Notes
Only `.xlsx` files are supported in the ABOSA output folders.

The pipeline uses a local `processed.json` file to track already processed folders and avoid redundant work.

All logs are stored in the `logs/` directory and timestamped for reproducibility.

