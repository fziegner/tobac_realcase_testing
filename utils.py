from glob import glob
import os
import git
import requests


def download_tobac(destination_dir, commit_hash, url=None):
    """Downloads a tobac version using commit hash from a specified URL.

    Parameters
    ----------
    destination_dir : str
        The directory where the tobac repository will be downloaded.
    commit_hash : str
        The commit hash to be downloaded.
    url : str
        The URL of the tobac repository. If not provided, the main tobac repository URL will be used.

    Returns
    -------
    repo_path : str
        The path to the downloaded repository.
    """
    if url:
        repo_url = url
    else:
        repo_url = f"https://github.com/tobac-project/tobac.git"
    repo_path = os.path.join(destination_dir, f"tobac_{commit_hash}")
    try:
        repo = git.Repo.clone_from(repo_url, repo_path, no_checkout=True)
        repo.git.checkout(commit_hash)
    except git.exc.GitCommandError:
        print(f"{repo_path} has to not exist.")

    return repo_path


def get_reference_file_paths(root_dir):
    """Gets the paths of all generated reference files.

    Parameters
    ----------
    root_dir : str
        The root directory from which to search for reference file paths.

    Returns
    -------
    file_paths : str
        A list of reference file paths.
    """
    file_paths = []

    for dir_path, dir_names, _ in os.walk(root_dir):
        for dir_name in [d for d in dir_names if d.startswith("Example")]:
            example_folder_path = os.path.join(dir_path, dir_name)
            file_paths.extend(glob(os.path.join(str(example_folder_path), "Save", "*")))
    return file_paths


def list_tags():
    """Retrieves the list of tags from the tobac-project repository.

    Returns
    -------
    tag_names : list
        A list of tag strings.
    """
    tags_url = f"https://api.github.com/repos/tobac-project/tobac/tags"
    tags_response = requests.get(tags_url)
    tags = tags_response.json()
    tag_names = [tag["name"] for tag in tags]

    return tag_names
