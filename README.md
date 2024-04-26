# Realcase Testing for Tobac

This is a tool for comparing reference files generated from Jupyter notebooks related to [tobac](https://github.com/tobac-project/tobac). It works by creating a Mamba environment and installing certain checkpoints of tobac that are then used to locally run example notebooks. The resulting .h5 and .nc files are then compared on a per variable/attribute basis. 


# INSTALLATION

1. Clone the repository
2. Make sure Mamba is installed

# USAGE AND OPTIONS

1. Open the repository folder in your terminal
2. Run `python realcase_testing.py` with your arguments

## Options:

Example call: `python ./realcase_testing.py -nb v1.5.2 -v1 1.5.2 -v2 v1.5.1 -s ./realcase_testing`

| Argument        | Function                                                                                                                                                         | Possibilities                                                          |
|-----------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| -nb, --notebook | For specifying the checkpoint for the notebooks. You may use the current working directory, an absolute/relative path to a directory or a GitHub version or hash | wd, ./examples, v1.5.2/1.5.2, 8f92d8030e9e402a1fc295bacfc703d9f6955498 |
| -v1, --version1 | First tobac version for comparison                                                                                                                               | v1.5.2/1.5.2, v1.5.1/1.5.1, ...                                        |
| -v2, --version2 | Second tobac version for comparison                                                                                                                              | v1.5.2/1.5.2, v1.5.1/1.5.1, ...                                        |
| -s,  --save     | The directory in which the environment and reference data should be saved. Either a directory in /tmp or a specified relative/absolute path                      | tmp, ./realcase_testing                                                |
| -n,  --names    | For choosing specific notebooks to test                                                                                                                          | [Example_OLR_Tracking_model, Example_Precip_Tracking]                  |

