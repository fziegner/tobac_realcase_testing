import argparse
import glob
import os

import git.exc
import nbformat
from git import Repo
from nbconvert.preprocessors import CellExecutionError
from nbconvert.preprocessors import ExecutePreprocessor

parser = argparse.ArgumentParser()
parser.add_argument("--version", type=str)  # for choosing notebook version; "wd", "PATH_TO_NOTEBOOK_FOLDER" or GitHub tobac version or hash
parser.add_argument("--save", type=str)  # for choosing save location of downloaded notebooks and output data; a path
parser.add_argument("--url", type=str)  # URL from which to download tobac
parser.add_argument("--names", default="All", type=str)  # Notebooks which should be executed; "All" or list delimited by comma

args = parser.parse_args()


def get_notebooks_paths(root_dir, notebooks_dir, exclude=None):
    """Gets all Jupyter notebook paths in a given directory.

    Parameters
    ----------
    root_dir : str
        Path to the directory in which the notebooks directory is located.
    notebooks_dir : str
        Name of the directory containing the notebooks.
    exclude : list, optional
        List of strings which should be excluded from the notebook search.

    Returns
    -------
    notebook_paths : list
        A list of paths to the notebooks.
    """

    notebooks_path = os.path.join(root_dir, notebooks_dir)
    return [
        os.path.join(path, file)
        for path, _, files in os.walk(notebooks_path)
        for file in files if file.endswith(".ipynb")
        and not (exclude and any(exc in path for exc in exclude))
    ]


def list_tags(repo_dir):
    """Gets all version tags of a local Git repository.

    Parameters
    ----------
    repo_dir : str
        Path to the repository directory.

    Returns
    -------
    repo_tags : list
        A list of all version tags in the repository, sorted by commit date (newest first).
    """

    tags = Repo(repo_dir).tags
    return sorted((tag.name for tag in tags), key=lambda t: t.commit.committed_datetime, reverse=True)


def get_notebook_files(method, environment_dir, notebook_dir, url="https://github.com/tobac-project/tobac"):
    """Gets a list of strings pointing to the notebook files.

    Parameters
    ----------
    method : str
        For selecting the notebook files. Possible values include "wd" (working directory), a path to existing notebooks, Git version tags, and commit hashes.
    environment_dir : str
        Path to the directory in which the environment is generated.
    notebook_dir : str
        Name of the directory containing the notebooks.
    url : str
        GitHub URL from which the repository should be cloned. Default is the main tobac repository.

    Returns
    -------
    notebook_paths : list
        A list of paths to the notebooks.
    """
    repo_dir = os.path.join(environment_dir, notebook_dir)
    print(repo_dir)

    if method == "wd":
        return get_notebooks_paths(os.getcwd(), "examples", ["Basics", "Track_on_Radar_Segment_on_Satellite"])
    elif os.path.exists(repo_dir):
        print(f"Existing notebook directory found at {repo_dir}.")
        return get_notebooks_paths(repo_dir, "examples", ["Basics", "Track_on_Radar_Segment_on_Satellite"])

    repo = Repo.clone_from(url, repo_dir, no_checkout=True)
    target = method

    while True:
        try:
            repo.git.checkout(target)
            break
        except git.exc.GitCommandError:
            target = input(f"Enter a valid version tag {list_tags(repo_dir)} or commit hash: ")

    return get_notebooks_paths(repo_dir, "examples", ["Basics", "Track_on_Radar_Segment_on_Satellite"])


def run_notebook(notebook_path, output_path):
    """Executes a Jupyter notebook given its file path.

    Parameters
    ----------
    notebook_path : str
        The file path of the Jupyter notebook to execute.
    output_path : str
        The output directory where the output of the notebook will be saved.
    """
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")

    try:
        print(f"Running notebook {notebook_path}")
        ep.preprocess(nb, {"metadata": {"path": output_path}})
        print(f"Notebook {notebook_path} executed successfully!")
    except CellExecutionError as e:
        print(f"Error executing the notebook {notebook_path}.\nSee the following error: {e}\n")
        raise


def create_reference_data(notebooks_paths, save_dir_path, notebook_names):
    """Creates reference data for given Jupyter notebooks.

    Parameters
    ----------
    notebooks_paths : list
        A list containing string paths pointing to individual notebooks.
    save_dir_path : str
        Path to the directory in which output of the notebooks should be saved.
    notebook_names : str | list
        For selecting which notebooks should be executed. Either "All" if all notebooks should be processed, or a list of notebook filenames.

    Returns
    -------
    reference_list : list
        A list containing string paths pointing to the output of all processed notebooks.
    """
    reference_list = []
    list_of_entries = [item for item in args.names.split(',')]

    if notebook_names == "All":
        list_of_entries = [os.path.basename(notebook).split(".")[0] for notebook in notebooks_paths]
    for notebook in notebooks_paths:
        notebook_name = os.path.basename(notebook).split(".")[0]
        if notebook_name in list_of_entries:
            output_path = os.path.join(save_dir_path, notebook_name)
            os.makedirs(output_path, exist_ok=True)
            run_notebook(notebook, output_path)
            reference_list.extend(glob.glob(os.path.join(output_path, "Save", "*")))

    return reference_list


def main():

    notebooks_paths = get_notebook_files(args.version, args.save, "./notebooks", args.url)
    create_reference_data(notebooks_paths, args.save, args.names)


if __name__ == "__main__":
    main()
