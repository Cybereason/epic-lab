# we expect the following external params to be preconfigured.
# these lines will fail if they don't (since we run with set -u).
gs_base_path="$gs_base_path"


# config

# Linux user
export USER_NAME=jupyter
export USER_GROUP_NAME=jupyter
export USER_ID=1200
export USER_GROUP_ID=1201
export USER_HOME="/home/${USER_NAME}"

# GCP secrets
export epic_lab_secret_ssh_key_private="epic-lab-ssh-key-private"
export epic_lab_secret_ssh_key_public="epic-lab-ssh-key-public"
export epic_lab_secret_jupyter_password="epic-lab-jupyter-password"

# GCP repos
export epic_lab_repo_notebooks="notebooks"
export epic_lab_repo_configuration="configuration"


# utils
user_exists() { id -u "$1" && echo "user $1 already exists"; }
file_exists() { test -e "$1"; }
prog_exists() { which "$1" && echo "prog $1 already exists"; }
line_exists() { grep "$1" "$2"; }
user_file_exists() { file_exists "$USER_HOME/$1"; }
service_exists() { systemctl list-unit-files | grep -E --silent "\b$1.service\b"; }
pip_installed() { $USER_HOME/conda/pip list | grep --silent "$1=="; }
source_from_gs() { source <(gsutil cat "$gs_base_path/$1"); }
run_from_gs() { gsutil cat "$gs_base_path/$1" | bash -; }
run_as_user() {
  commands=$(</dev/stdin)
  su - $USER_NAME <<END
  set -u
  set -e
  $commands
END
}

# metadata
instance_name=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/name)
export instance_name
instance_external_ip=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip)
export instance_external_ip
