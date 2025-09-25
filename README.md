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

ABOSA_OUTPUT_PATH=/abosa-output
LOG_OUTPUT_PATH=/app/logs
```

The .env file must be placed at the root of the project, next to pyproject.toml.

It is automatically loaded using the `python-dotenv` library in the appropriate modules.

**Do not version this file**: it is excluded by .gitignore.

### Docker

The project includes a `Dockerfile` to enable isolated and portable execution.

Build the Docker image :
```bash
docker build -t indicator-pipeline .
```

**Windows users**: Ensure Docker Desktop is allowed to access your local drive (e.g., `C:`) in Docker settings.

## Main Script

### Snakemake Workflow (Recommended)

For a fully orchestrated, reproducible execution:

```bash
snakemake --cores 1
```

You can customize the years to process using the `--config` argument:

```bash
snakemake --config years="2023 2024" --cores 1 
```
If this argument is not provided, the **current year** is used by default.

Snakemake will:
- Run the `slf_conversion` step. 
- Pause for manual processing in ABOSA. 
- Resume with the `import_to_mars` step.

Snakemake uses flag files to manage execution state:

- `step1.done`: Marks completion of the SLF conversion
- `manual_ready.flag`: Created manually after ABOSA is run (the file `create_flag.bat` allows to create this file)
- `step2.done`: Marks successful import to the MARS database

After the execution of the whole pipeline, these control files can be deleted by launching:
```bash
snakemake clean --cores 1
```

📝 The Snakefile assumes data is saved on the user's Desktop (`~/Desktop`). If you're working elsewhere, edit the paths in Snakefile (`SLF_OUTPUT`, `LOGS_DIR`, `ABOSA_OUTPUT`, etc.).

### Manual Script Execution (Alternative)
To execute the pipeline manually:

```bash
run-pipeline --step slf_conversion --years 2023 2024
```

Then, after running ABOSA manually, launch:
```bash
run-pipeline --step import_to_mars
```

### Arguments
`--step`: Required, either `slf_conversion` or `import_to_mars`

`--years`: Required for slf_conversion, space-separated list of years to process (e.g., --years 2023 2024)

## Additional Notes
Only `.xlsx` files are supported in the ABOSA output folders.

The pipeline uses a local `processed.json` file to track already processed folders and avoid redundant work.

All logs are stored in the `logs/` directory and timestamped for reproducibility.

