import argparse
import glob
import os
import subprocess
import tempfile
import requests
import platform

import xarray as xr

parser = argparse.ArgumentParser()
parser.add_argument("-nb", "--notebook", type=str)  # for choosing notebook version; "local", "PATH_TO_NOTEBOOK_FOLDER" or GitHub tobac version or hash
parser.add_argument("-v1", "--version1", type=str)  # first comparison version; "X.Y.Z" or "vX.Y.Z"
parser.add_argument("-v2", "--version2", type=str)  # second comparison version; "X.Y.Z" or "vX.Y.Z"
parser.add_argument("-s", "--save", type=str)  # for choosing save location of envs and reference data; "tmp" or "PATH_TO_SAVE_FOLDER"
# TODO: Separate env folder
args = parser.parse_args()

kwargs = {}
plt = platform.system()
if plt == "Windows":
    kwargs["shell"] = True

def create_environment(environment_path, tobac_version):

    if tobac_version.startswith("v"):
        tobac_version = tobac_version[1::]

    normalized_prefix = environment_path.rstrip('/')
    envs = subprocess.check_output(['mamba', 'env', 'list'], **kwargs).decode('utf-8')
    envs_info = envs.split('\n')

    for env_info in envs_info:
        parts = env_info.split()
        if len(parts) == 1:
            if os.sep in parts[0]:
                if normalized_prefix in parts[0]:
                    print(f"Conda environment at '{environment_path}' already exists.")
                    subprocess.run(["mamba", "install", "-y", "-p", environment_path, "-c", "conda-forge", f"tobac={tobac_version}", "--file", "conda_requirements.txt"], check=True, **kwargs)
                    return False

    print(f"Creating new environment at {environment_path}")
    subprocess.run(["mamba", "create", "-y", "-p", environment_path, "python"], check=True, **kwargs)
    subprocess.run(["mamba", "install", "-y", "-p", environment_path, "-c", "conda-forge", f"tobac={tobac_version}", "--file", "conda_requirements.txt"], check=True, **kwargs)


def get_reference_file_paths(root_dir):

    file_paths = []

    for dir_path, dir_names, file_names in os.walk(root_dir):
        for dir_name in [d for d in dir_names if d.startswith("Example")]:
            example_folder_path = os.path.join(dir_path, dir_name)
            file_paths.extend(glob.glob(os.path.join(example_folder_path, "Save", "*")))
    return file_paths


def compare_files_detailed(reference_file1, reference_file2):

    # TODO: Clear file
    with open("comparison_results.txt", "a") as f:
        with xr.open_dataset(reference_file1) as ds_source, xr.open_dataset(reference_file2) as ds_target:
            if ds_source.equals(ds_target):
                print(f"Comparison result for {reference_file1} and {reference_file2}: Same")
                f.write(f"Comparison result for {reference_file1} and {reference_file2}: Same\n")
            else:
                print(f"Comparison result for {reference_file1} and {reference_file2}: Different")
                f.write(f"Comparison result for {reference_file1} and {reference_file2}: Different\n")
                for attribute in set(ds_source.attrs).union(ds_target.attrs):
                    if attribute not in ds_source.attrs or attribute not in ds_target.attrs or ds_source.attrs[attribute] != ds_target.attrs[attribute]:
                        print(f"Global attribute '{attribute}' differs.")
                        f.write(f"Global attribute '{attribute}' differs.\n")

                for variable in set(ds_source.variables).union(ds_target.variables):
                    if variable not in ds_source.variables or variable not in ds_target.variables:
                        print(f"Variable '{variable}' is not present in both files.")
                        f.write(f"Variable '{variable}' is not present in both files.\n")
                    else:
                        for attribute in set(ds_source[variable].attrs).union(ds_target[variable].attrs):
                            if attribute not in ds_source[variable].attrs or attribute not in ds_target[variable].attrs or ds_source[variable].attrs[attribute] != ds_target[variable].attrs[attribute]:
                                print(f"Attribute '{attribute}' of variable '{variable}' differs.")
                                f.write(f"Attribute '{attribute}' of variable '{variable}' differs.\n")

                        if not ds_source[variable].equals(ds_target[variable]):
                            print(f"Data of variable '{variable}' differs.")
                            f.write(f"Data of variable '{variable}' differs.\n")


def list_tags():

    tags_url = f"https://api.github.com/repos/tobac-project/tobac/tags"
    tags_response = requests.get(tags_url)
    tags = tags_response.json()
    tag_names = [tag['name'] for tag in tags]

    return tag_names


def check_version(tobac_version):

    tags = list_tags()
    if not tobac_version.startswith("v"):
        tobac_version = "v" + tobac_version
    if tobac_version in tags:
        return tobac_version[1::]
    else:
        print(f"Enter a valid tobac version tag {tags}")
        exit()


def main():

    if args.save == "tmp":
        save_directory = tempfile.TemporaryDirectory()
    else:
        save_directory = args.save

    environment_name = "realcase_testing"
    environment_path = os.path.join(save_directory, environment_name)

    tobac_version = check_version(args.version1)
    create_environment(environment_path, tobac_version)
    subprocess.run(["mamba", "run", "-p", environment_path, "python", "create_references.py", "--nb", args.notebook, "--sv", save_directory, "--name", "source_reference_data"], check=True, **kwargs)
    source_paths = get_reference_file_paths(os.path.join(save_directory, "source_reference_data"))

    tobac_version = check_version(args.version2)
    subprocess.run(["mamba", "install", "-y", "-c", "conda-forge", "-p", environment_path, f"tobac={tobac_version}"], check=True, **kwargs)
    subprocess.run(["mamba", "run", "-p", environment_path, "python", "create_references.py", "--nb", args.notebook, "--sv", save_directory, "--name", "target_reference_data"], check=True, **kwargs)

    for source_path in source_paths:
        target_path = source_path.replace("source_reference_data", "target_reference_data")
        if os.path.exists(target_path):
            compare_files_detailed(source_path, target_path)

    if args.save == "tmp":
        save_directory.cleanup()


#  python .\realcase_testing.py -nb v1.5.2 -v1 v1.5.2 -v2 v1.5.1 -s ./testing
if __name__ == "__main__":
    main()
