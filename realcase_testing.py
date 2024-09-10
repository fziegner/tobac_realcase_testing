import argparse
import glob
import os
import subprocess
import tempfile
import requests
import platform
import re
import git
import utils

import xarray as xr

parser = argparse.ArgumentParser()
parser.add_argument("-nb", "--notebook", type=str)  # for choosing notebook version; "local", "PATH_TO_NOTEBOOK_FOLDER" or GitHub tobac version or hash
parser.add_argument("-v1", "--version1", type=str)  # first comparison version; "X.Y.Z" or "vX.Y.Z"
parser.add_argument("-v1u", "--version1url", default=None, type=str)  # first comparison version url
parser.add_argument("-v2", "--version2", type=str)  # second comparison version; "X.Y.Z" or "vX.Y.Z"
parser.add_argument("-v2u", "--version2url", default=None, type=str)  # second comparison version url
parser.add_argument("-s", "--save", type=str)  # For choosing save location of the generated environment and notebook outputs; "tmp" or "PATH_TO_SAVE_FOLDER"
parser.add_argument("-na", "--names", default="All", type=str)  # for choosing specific notebooks to test; should be the names of the notebooks as they are called in the tobac examples folder delimited by a comma, e.g. Example_OLR_Tracking_model,Example_Precip_Tracking

args = parser.parse_args()

plt = platform.system()
kwargs = {"shell": True} if plt == "Windows" else {}

pattern_version = r"^v?\d+\.\d+\.\d+$"
pattern_commit = r"^[0-9a-fA-F]{40}$"


def create_environment(environment_path, tobac_version, url, existing_env):
    """Creates a mamba environment.

    Parameters
    ----------
    environment_path : str
        The path where the environment will be created.
    tobac_version : str
        The version of Tobac to be installed in the environment.
    url : str
        The URL from which Tobac will be downloaded.
    existing_env : bool
        Flag indicating whether it is the second version of Tobac. Default is False.
    """

    if tobac_version.startswith("v"):
        tobac_version = tobac_version[1::]

    normalized_prefix = environment_path.rstrip("/")
    envs = subprocess.check_output(["mamba", "env", "list"], **kwargs).decode("utf-8")
    envs_info = envs.split("\n")
    utils.download_tobac(environment_path, tobac_version, url)

    if not existing_env:
        exists = False
        for env_info in envs_info:
            parts = env_info.split()
            if len(parts) == 1:
                if os.sep in parts[0]:
                    if normalized_prefix in parts[0]:
                        print(f"Conda environment at '{environment_path}' already exists.")
                        exists = True
        if not exists:
            print(f"Creating new environment at {environment_path}")
            subprocess.run(
                ["mamba", "create", "-y", "-p", environment_path, "python"],
                check=True,
                **kwargs,
            )
    if re.match(pattern_version, tobac_version):
        subprocess.run(
            [
                "mamba",
                "install",
                "-y",
                "-p",
                environment_path,
                "-c",
                "conda-forge",
                f"tobac={tobac_version}",
                "--file",
                "conda_requirements.txt",
            ],
            check=True,
            **kwargs,
        )
    elif bool(re.match(pattern_commit, tobac_version)):
        print("Hash detected")
        subprocess.run(
            [
                "mamba",
                "install",
                "-y",
                "-p",
                environment_path,
                "-c",
                "conda-forge",
                "--file",
                "conda_requirements.txt",
                "--file",
                os.path.join(environment_path, f"tobac_{tobac_version}", "requirements.txt"),
                "--file",
                os.path.join(environment_path, f"tobac_{tobac_version}", "example_requirements.txt"),
            ],
            check=True,
            **kwargs,
        )
        if plt != "Windows":
            subprocess.run(
                [
                    str(os.path.join(os.getcwd(), environment_path, "bin", "pip")),
                    "install",
                    "--no-deps",
                    "--prefix",
                    environment_path,
                    os.path.join(environment_path, f"tobac_{tobac_version}"),
                ],
                check=True,
                **kwargs,
            )
        else:
            subprocess.run(
                [
                    str(os.path.join(os.getcwd(), environment_path, "Scripts", "pip")),
                    "install",
                    "--no-deps",
                    "--prefix",
                    environment_path,
                    os.path.join(environment_path, f"tobac_{tobac_version}"),
                ],
                check=True,
                **kwargs,
            )
    else:
        print("Tobac version not valid.")
        exit()


def check_version(tobac_version):
    """
    This function checks the version of 'tobac'. The version can be specified in two formats: a git commit hash or a version tag.

    Parameters
    ----------
    tobac_version: str
        The version of tobac. Can be a git commit hash or a version tag.

    Returns
    -------
    tobac_version: str
        The tobac version without the preceding "v" if it is a valid version tag. If the 'tobac_version' is a git commit
        hash, it returns it as it is. If an invalid version is given, a list of possible versions is returned.
    """

    tags = utils.list_tags()
    if re.match(pattern_commit, tobac_version):
        return tobac_version
    if not tobac_version.startswith("v"):
        tobac_version = "v" + tobac_version
    if tobac_version in tags:
        return tobac_version[1:]
    print(f"Invalid version or hash. Valid versions: {tags}")
    exit()


def process_version(tobac_version, version_url, environment_path, save_dir, existing_env=False):
    """Runs all notebooks found in the Repository of a given Tobac version. Version provided by either a git commit hash
    or a version tag.

    Parameters
    ----------
    tobac_version : str
        The tobac version to install, either a git commit hash or a version tag.
    version_url : str
        The URL for the version from which the notebooks are downloaded.
    environment_path : str
        The path to the environment.
    save_dir : str
        The directory in which downloaded notebooks and their output will be saved.
    existing_env : bool
        Flag indicating whether it is the second version of Tobac. This flag exists so that the previously created
        environment can be reused. Default is False.
    """
    version_url = version_url or "https://github.com/tobac-project/tobac"
    tobac_version = check_version(tobac_version)
    create_environment(environment_path, tobac_version, version_url, existing_env)

    subprocess.run(
        ["mamba", "run", "-p", environment_path, "python", "create_references.py", "--version", args.notebook, "--save", save_dir, "--url", version_url, "--names", args.names],
        check=True, **kwargs,
    )


def compare_files_detailed(reference_file1, reference_file2):
    """Compares two datasets and checks whether they are equal."""
    with open("comparison_results.txt", "a") as f:
        with xr.open_dataset(reference_file1) as ds_source, xr.open_dataset(reference_file2) as ds_target:
            if ds_source.equals(ds_target):
                result = f"Comparison result for {reference_file1} and {reference_file2}: Same\n"
                print(result.strip())
                f.write(result)
            else:
                result = f"Comparison result for {reference_file1} and {reference_file2}: Different\n"
                print(result.strip())
                f.write(result)
                diff_report(ds_source, ds_target, f)


def diff_report(ds_source, ds_target, output_file):
    """Reports differences between two datasets."""
    for attr in set(ds_source.attrs).union(ds_target.attrs):
        if ds_source.attrs.get(attr) != ds_target.attrs.get(attr):
            output_file.write(f"Global attribute '{attr}' differs.\n")

    for var in set(ds_source.variables).union(ds_target.variables):
        if var not in ds_source or var not in ds_target:
            output_file.write(f"Variable '{var}' is not present in both files.\n")
        else:
            compare_variable(ds_source, ds_target, var, output_file)


def compare_variable(ds_source, ds_target, var, output_file):
    """Compares a variable in two datasets and writes differences."""
    for attr in set(ds_source[var].attrs).union(ds_target[var].attrs):
        if ds_source[var].attrs.get(attr) != ds_target[var].attrs.get(attr):
            output_file.write(f"Attribute '{attr}' of variable '{var}' differs.\n")

    if not ds_source[var].equals(ds_target[var]):
        output_file.write(f"Data of variable '{var}' differs.\n")


def main():

    save_directory = tempfile.TemporaryDirectory() if args.save == "tmp" else args.save
    environment_path = os.path.join(save_directory, "realcase_testing")

    process_version(args.version1, args.version1url, environment_path, os.path.join(save_directory, "source_reference_data"))
    source_paths = utils.get_reference_file_paths(os.path.join(save_directory, "source_reference_data"))

    process_version(args.version2, args.version2url, environment_path, os.path.join(save_directory, "target_reference_data"), True)
    for source_path in source_paths:
        target_path = source_path.replace("source_reference_data", "target_reference_data")
        if os.path.exists(target_path):
            compare_files_detailed(source_path, target_path)

    if args.save == "tmp":
        save_directory.cleanup()


if __name__ == "__main__":
    main()
