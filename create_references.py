import argparse
import glob
import os

import git.exc
import nbformat
from git import Repo
from nbconvert.preprocessors import CellExecutionError
from nbconvert.preprocessors import ExecutePreprocessor

parser = argparse.ArgumentParser()
parser.add_argument("--nb", type=str)
parser.add_argument("--sv", type=str)
parser.add_argument("--name", type=str)
args = parser.parse_args()


# Configuration
REPOSITORY_URL = f"https://github.com/tobac-project/tobac.git"


def get_notebooks_paths(root_dir, notebooks_folder):
    notebooks_path = os.path.join(root_dir, notebooks_folder)
    notebook_paths = []
    for path, dirs, files in os.walk(notebooks_path):
        for file in files:
            if file.endswith(".ipynb"):
                notebook_paths.append(os.path.join(path, file))
    return notebook_paths


def get_head_notebooks(repo_path):

    repo = Repo(repo_path)

    head_tree = repo.head.commit.tree
    notebook_paths = [blob.path for blob in head_tree.traverse() if blob.path.startswith("examples") and blob.path.endswith(".ipynb")]
    print(notebook_paths)
    return notebook_paths


def read_file_in_head(repo_path, file_path):

    repo = Repo(repo_path)

    file_blob = repo.head.commit.tree / file_path
    file_content = file_blob.data_stream.read().decode("utf-8")

    return file_content


def list_tags(repo_path):
    repo = Repo(repo_path)
    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    return [tag.name for tag in tags]


def get_notebook_files(arg_nb, save_directory_path, save_directory_name):

    save_directory = os.path.join(save_directory_path, save_directory_name)

    if arg_nb == "wd":
        return get_notebooks_paths(os.getcwd(), "examples")
    elif os.path.exists(os.path.join(save_directory, "examples")):
        return get_notebooks_paths(save_directory, "examples")
    else:  # for versions and hashes
        repo = Repo.clone_from(REPOSITORY_URL, save_directory, no_checkout=True)
        target = arg_nb
        while True:
            try:
                repo.git.checkout(target)
                break
            except git.exc.GitCommandError:
                target = input(f"Enter a valid version tag {list_tags(save_directory)} or commit hash: ")
                continue
        return get_notebooks_paths(save_directory, "examples")


def run_notebook(notebook_path, output):

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")

    try:
        print(f"Running notebook {notebook_path}")
        ep.preprocess(nb, {"metadata": {"path": output}})
        print(f"Notebook {notebook_path} executed successfully!")
    except CellExecutionError as e:
        msg = f"Error executing the notebook {notebook_path}.\n"
        msg += f"See the following error: {e}\n"
        print(msg)
        raise


def create_reference_data(source_directory, save_directory_path, save_directory_name):

    # TODO: Choosable notebooks
    reference_list = []

    for notebook in source_directory:
        notebook_name = os.path.basename(notebook).split(".")[0]  # get notebook name without extension
        output_path = os.path.join(save_directory_path, save_directory_name, notebook_name)
        os.makedirs(output_path)
        run_notebook(notebook, output_path)
        reference_list.extend(glob.glob(os.path.join(output_path, "Save", "*")))
        break

    return reference_list


def main():

    source_notebooks = get_notebook_files(args.nb, args.sv, "notebooks")
    create_reference_data(source_notebooks, args.sv, args.name)


if __name__ == "__main__":
    main()