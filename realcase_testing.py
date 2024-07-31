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
parser.add_argument(
    "-nb", "--notebook", type=str
)  # for choosing notebook version; "local", "PATH_TO_NOTEBOOK_FOLDER" or GitHub tobac version or hash
parser.add_argument(
    "-v1", "--version1", type=str
)  # first comparison version; "X.Y.Z" or "vX.Y.Z"
parser.add_argument(
    "-v1u", "--version1url", default=None, type=str
)  # first comparison version url
parser.add_argument(
    "-v2", "--version2", type=str
)  # second comparison version; "X.Y.Z" or "vX.Y.Z"
parser.add_argument(
    "-v2u", "--version2url", default=None, type=str
)  # second comparison version url
parser.add_argument(
    "-s", "--save", type=str
)  # For choosing save location of the generated environment and notebook outputs; "tmp" or "PATH_TO_SAVE_FOLDER"
parser.add_argument(
    "-na", "--names", default="All", type=str
)  # for choosing specific notebooks to test; should be the names of the notebooks as they are called in the tobac
   # examples folder delimited by a comma, e.g. Example_OLR_Tracking_model,Example_Precip_Tracking

args = parser.parse_args()

kwargs = {}
plt = platform.system()
if plt == "Windows":
    kwargs["shell"] = True

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
            ],
            check=True,
            **kwargs,
        )
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
    if bool(re.match(pattern_commit, tobac_version)):
        return tobac_version
    if not tobac_version.startswith("v"):
        tobac_version = "v" + tobac_version
    if tobac_version in tags:
        return tobac_version[1::]
    else:
        print(f"Enter a valid hash or tobac version tag {tags}")
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
    if version_url is None:
        version_url = "https://github.com/tobac-project/tobac"
    tobac_version = check_version(tobac_version)
    create_environment(environment_path, tobac_version, version_url, existing_env)
    subprocess.run(
        [
            "mamba",
            "run",
            "-p",
            environment_path,
            "python",
            "create_references.py",
            "--version",
            args.notebook,
            "--save",
            save_dir,
            "--url",
            version_url,
            "--names",
            args.names,
        ],
        check=True,
        **kwargs,
    )


def compare_files_detailed(reference_file1, reference_file2):
    """Compares two datasets and checks whether they are equal by comparing global attributes and variables.
    Reports mismatches if found. Results are written to a file.

    Parameters
    ----------
    reference_file1 : str
        The path to the first reference file.
    reference_file2 : str
        The path to the second reference file.
    """

    with open("comparison_results.txt", "a") as f:
        with xr.open_dataset(reference_file1) as ds_source, xr.open_dataset(
            reference_file2
        ) as ds_target:
            if ds_source.equals(ds_target):
                print(
                    f"Comparison result for {reference_file1} and {reference_file2}: Same"
                )
                f.write(
                    f"Comparison result for {reference_file1} and {reference_file2}: Same\n"
                )
            else:
                print(
                    f"Comparison result for {reference_file1} and {reference_file2}: Different"
                )
                f.write(
                    f"Comparison result for {reference_file1} and {reference_file2}: Different\n"
                )
                for attribute in set(ds_source.attrs).union(ds_target.attrs):
                    if (
                        attribute not in ds_source.attrs
                        or attribute not in ds_target.attrs
                        or ds_source.attrs[attribute] != ds_target.attrs[attribute]
                    ):
                        print(f"Global attribute '{attribute}' differs.")
                        f.write(f"Global attribute '{attribute}' differs.\n")

                for variable in set(ds_source.variables).union(ds_target.variables):
                    if (
                        variable not in ds_source.variables
                        or variable not in ds_target.variables
                    ):
                        print(f"Variable '{variable}' is not present in both files.")
                        f.write(
                            f"Variable '{variable}' is not present in both files.\n"
                        )
                    else:
                        for attribute in set(ds_source[variable].attrs).union(
                            ds_target[variable].attrs
                        ):
                            if (
                                attribute not in ds_source[variable].attrs
                                or attribute not in ds_target[variable].attrs
                                or ds_source[variable].attrs[attribute]
                                != ds_target[variable].attrs[attribute]
                            ):
                                print(
                                    f"Attribute '{attribute}' of variable '{variable}' differs."
                                )
                                f.write(
                                    f"Attribute '{attribute}' of variable '{variable}' differs.\n"
                                )

                        if not ds_source[variable].equals(ds_target[variable]):
                            print(f"Data of variable '{variable}' differs.")
                            f.write(f"Data of variable '{variable}' differs.\n")


def main():

    if args.save == "tmp":
        save_directory = tempfile.TemporaryDirectory()
    else:
        save_directory = args.save

    environment_name = "realcase_testing"
    environment_path = os.path.join(save_directory, environment_name)

    process_version(args.version1, args.version1url, environment_path, os.path.join(save_directory, "source_reference_data"))
    source_paths = utils.get_reference_file_paths(
        os.path.join(save_directory, "source_reference_data")
    )

    process_version(args.version2, args.version2url, environment_path, os.path.join(save_directory, "target_reference_data"), True)
    for source_path in source_paths:
        target_path = source_path.replace(
            "source_reference_data", "target_reference_data"
        )
        if os.path.exists(target_path):
            compare_files_detailed(source_path, target_path)

    if args.save == "tmp":
        save_directory.cleanup()


#  python .\realcase_testing.py -nb v1.5.2 -v1 v1.5.2 -v2 v1.5.1 -s ./testing
if __name__ == "__main__":
    main()
