import subprocess
from os.path import dirname, join, abspath
from sys import argv, exit

USAGE = """\
Usage: python -m epic.lab <command>

Commands:
    `synccode`:
        Run the `epic-synccode` sub-command.
        For more details, run `epic-lab synccode help`.
    
    `notebook`:
        Run the `epic-notebook` sub-command.
        For more details, run `epic-lab notebook help`.

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


def _script_path(name):
    return join(dirname(__file__), "scripts", name)


def main():
    cmd = argv[1] if argv[1:] else None
    if cmd == "vmsetup-path":
        vmsetup_path()
    elif cmd == "synccode":
        exit(subprocess.call([_script_path("epic-synccode")] + argv[2:]))
    if cmd == "notebook":
        exit(subprocess.call([_script_path("epic-notebook")] + argv[2:]))
    else:
        print(USAGE)
        exit(1)
