from os.path import dirname, join, abspath
from sys import argv, exit

USAGE = """\
Usage: python -m epic.lab <command>

Commands:
    `vmsetup-path`:
        Print the absolute path to the vmsetup folder.
        Use this when creating a new notebook setup version, with commands such as the following:
        $ vm_setup_version="vmsetup_$(date +%Y%m%d)"
        $ vm_setup_path=$(python -m epic.lab vmsetup-path)
        $ gs_base_path=gs://your_epic_lab_bucket
        $ gcloud storage cp ${vm_setup_path}/** "$gs_base_path/$vm_setup_version"
        $ test -f additional_on_create.sh && gcloud storage cp additional_on_create.sh "$gs_base_path/$vm_setup_version"
"""


def vmsetup_path():
    print(abspath(join(dirname(__file__), "vmsetup")))


if argv[1] == "vmsetup-path":
    vmsetup_path()
else:
    print(USAGE)
    exit(1)
