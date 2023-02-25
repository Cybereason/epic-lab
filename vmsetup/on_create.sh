#!/bin/bash
# TODO: for some reason, this script is also running on resume of the VM, not just on creation
set -u
set -e

# we export all variables and functions for the benefit of the additional setup scripts, if they exist
set -o allexport

# validate operating system
which lsb_release
lsb_release -a
lsb_release -a 2>&1 | grep --silent "Ubuntu"

# include
source <(gsutil cat "$gs_base_path/common.sh")


# persistent directory utils

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUNDIR="/root/epic-lab-vmsetup/${TIMESTAMP}"

fetch_gs_script() {
  gsutil cp "$gs_base_path/$1" "$RUNDIR/$1"
  chmod +x "$RUNDIR/$1"
}


# script

echo "epic-lab: starting on-create script"

mkdir -p "$RUNDIR" && cd "$RUNDIR"

user_exists "$USER_NAME" || {
  echo "creating user $USER_NAME ($USER_ID)"
  groupadd -g "$USER_GROUP_ID" "$USER_GROUP_NAME"
  adduser --uid "$USER_ID" --gid "$USER_GROUP_ID" --disabled-password --gecos "" "$USER_NAME"
  echo "$USER_NAME ALL=(ALL) NOPASSWD: ALL" | tee -a /etc/sudoers
}

prog_exists jq || {
  echo "installing required tools"
  apt-get update
  apt-get install -y jq make autossh zip
}

prog_exists gcc-10 || {
  # install and set default a new-enough version for gcc/gcc-c++ (note: locks us to v10)
  echo "installing gcc-10 and setting as default"
  apt-get install -y software-properties-common
  add-apt-repository -y ppa:ubuntu-toolchain-r/test
  apt-get update
  apt-get install -y gcc-10 g++-10
  update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-10 10
  update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-10 10
}

user_file_exists .ssh || run_as_user <<END
  echo "downloading epic-lab SSH keys into $USER_NAME user from secrets manager"
  mkdir ~/.ssh
  gcloud secrets versions access latest --secret="$epic_lab_secret_ssh_key_private" > ~/.ssh/epic-lab
  gcloud secrets versions access latest --secret="$epic_lab_secret_ssh_key_public" > ~/.ssh/epic-lab.pub
  cat ~/.ssh/epic-lab.pub >> ~/.ssh/authorized_keys
  tee -a ~/.ssh/config << EOT
# if you're forking this library, you may want to add some configs here
# here are some examples:

# Host github.com
#     IdentityFile ~/.ssh/epic-lab
#     StrictHostKeyChecking no

# Host bastion epic-lab-bastion
#     IdentityFile ~/.ssh/epic-lab
#     HostName 1.2.3.4
#     User username
EOT
  chmod 700 ~/.ssh
  chmod 600 ~/.ssh/config
  chmod 600 ~/.ssh/epic-lab
  chmod 600 ~/.ssh/authorized_keys
END

user_file_exists .screenrc || run_as_user <<END
  cat << EOT > ~/.screenrc
caption always
caption string "%{.bW}%-w%{.rW}%n %t%{-}%+w %=%{..G} %H %{..Y} %m/%d %C%a "

termcapinfo xterm* ti@:te@
EOT
END

prog_exists node || {
  curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
  apt-get install -y nodejs
  echo "node version: $(node -v)"
}

user_file_exists conda || run_as_user <<'END'
  echo "installing miniconda"
  # note: we really need python 3.10, but Miniconda3 hasn't released a "Miniconda3-py310..." release yet.
  wget -q https://repo.anaconda.com/miniconda/Miniconda3-py39_4.9.2-Linux-x86_64.sh
  bash ./Miniconda3-py39_4.9.2-Linux-x86_64.sh -b -p ~/conda
  rm ./Miniconda3-py39_4.9.2-Linux-x86_64.sh

  export PATH="~/conda/bin:$PATH"
  conda init

  # echo "updating conda"
  # conda update -y conda

  # there is an issue when running conda update and then upgrading to python 3.10
  # similar to the issue for which this was suggested as a workaround:
  # https://github.com/deepmind/alphafold/issues/573#issuecomment-1225955055
  echo "resetting conda to a very specific version"
  conda install -y conda==4.13.0

  # upgrade to python 3.10, since Miniconda3 does not yet come with it preinstalled
  # note: for some reason, this breaks the current user session. hopefully without further side effects.
  #       this is why we END the session here and start a new one right after.
  conda install -y python=3.10
END

user_file_exists conda/bin/jupyter || run_as_user <<END
  echo "installing packages"
  $USER_HOME/conda/bin/conda install -y -c conda-forge \
    pip \
    jupyterlab \
    ipywidgets

  $USER_HOME/conda/bin/conda update -y wheel

  echo "pip installing some more packages"
  $USER_HOME/conda/bin/pip install \
    google-cloud-storage \
    'google-cloud-bigquery[pandas]' \
    'jedi>=0.18.0'

  echo "install extension @jupyterlab/git and deps"
  $USER_HOME/conda/bin/pip install jupyterlab-git
  $USER_HOME/conda/bin/jupyter labextension install @jupyterlab/git

  # additional packages (some with pinned versions)
  $USER_HOME/conda/bin/conda install -y \
    numpy~=1.21.5 \
    pandas~=1.4.4 \
    matplotlib~=3.5.2 \
    scikit-learn~=1.1.1 \
    \
    cython==0.29.32 \
    pybind11~=2.9.2 \
    \
    networkx~=2.8.4 \
    lz4 \
    tqdm \
    dill \
    cytoolz

  # install the core epic-framework libraries
  $USER_HOME/conda/bin/pip install -U --extra-index-url https://d2dsindf03djlb.cloudfront.net \
    epic-common \
    epic-logging \
    epic-caching \
    epic-serialize \
    epic-jupyter \
    epic-pandas \
    ultima

  # note: if you fork this library, and modify the python packages, adjust this command to install your code
  $USER_HOME/conda/bin/pip install -U --extra-index-url https://d2dsindf03djlb.cloudfront.net \
    epic-lab
END

user_file_exists .jupyter/jupyter_notebook_config.py || run_as_user <<END
  echo "setting up jupyter-notebook"
  $USER_HOME/conda/bin/jupyter notebook --generate-config

  cat << EOT >> ~/.jupyter/jupyter_notebook_config.py
c.NotebookApp.ip = '0.0.0.0'
c.NotebookApp.port = 8080
c.NotebookApp.open_browser = False
c.LabApp.base_url = '$instance_name'
EOT
END

user_file_exists .jupyter/jupyter_notebook_config.json || run_as_user <<END
  gcloud secrets versions access latest --secret="$epic_lab_secret_jupyter_password" > ~/.jupyter/jupyter_notebook_config.json
END

user_file_exists notebooks || run_as_user <<END
  echo "cloning notebooks repo"
  gcloud source repos clone "$epic_lab_repo_notebooks"
END

# jupyter lab service
service_exists jupyter-lab || {
  echo "setting up jupyter-lab service"
  run_as_user <<<'mkdir -p ~/jupyter_lab/log'
  cat <<END >>/etc/systemd/system/jupyter-lab.service
[Unit]
Description=Jupyter LAB daemon

[Service]
Type=simple
PIDFile=/run/jupyter-lab.pid
ExecStart=/bin/bash -l -c "$USER_HOME/conda/bin/jupyter lab --config=$USER_HOME/.jupyter/jupyter_notebook_config.py --debug >> $USER_HOME/jupyter_lab/log/jupyter-lab.log 2>&1"
User=$USER_NAME
Group=$USER_GROUP_NAME
WorkingDirectory=$USER_HOME
Restart=always
RestartSec=5
MemoryHigh=85%
MemoryMax=92%

[Install]
WantedBy=multi-user.target
END
  systemctl enable jupyter-lab
  systemctl daemon-reload
  systemctl start jupyter-lab
  systemctl status jupyter-lab
}

service_exists stackdriver-agent || {
  # note: debug with this: sudo grep collectd /var/log/{syslog,messages} | tail
  wget https://dl.google.com/cloudagents/add-monitoring-agent-repo.sh
  bash add-monitoring-agent-repo.sh --also-install
  systemctl start stackdriver-agent
  systemctl status stackdriver-agent
  rm add-monitoring-agent-repo.sh
}

service_exists epic-lab-on-resume || {
  fetch_gs_script on_resume.sh
  cat <<END >>/etc/systemd/system/epic-lab-on-resume.service
[Unit]
Description=epic-lab on-resume handler
After=suspend.target

[Service]
Type=simple
Environment=gs_base_path=$gs_base_path
ExecStart=/bin/bash "$RUNDIR/on_resume.sh"
WorkingDirectory=$RUNDIR

[Install]
WantedBy=suspend.target
END
  systemctl enable epic-lab-on-resume
  systemctl daemon-reload
}

service_exists epic-lab-on-start || {
  fetch_gs_script on_start.sh
  cat <<END >>/etc/systemd/system/epic-lab-on-start.service
[Unit]
Description=epic-lab on-start handler

[Service]
Environment=gs_base_path=$gs_base_path
ExecStart=/bin/bash "$RUNDIR/on_start.sh"
WorkingDirectory=$RUNDIR

[Install]
WantedBy=multi-user.target
END
  systemctl enable epic-lab-on-start
  systemctl daemon-reload
}

user_file_exists username || run_as_user <<'END'
  individual_user=$(echo $HOSTNAME | grep -Eo '^[a-zA-Z]+')
  echo -n "$individual_user" > ~/username
END

user_file_exists synccode || run_as_user <<END
  echo "configuring synccode for cloud vm"
  bucket=\$(echo "$gs_base_path" | grep -Po '(?<=^gs://)([^/]+)')
  $USER_HOME/conda/bin/epic-synccode configure-vm "\$bucket" "synccode"
END

user_file_exists .ipython/profile_default || run_as_user <<END
  $USER_HOME/conda/bin/ipython profile create
  cat << EOT > ~/.ipython/profile_default/startup/startup_generic.py
from epic.lab.ipython_startup import *
EOT
END

# user-specific configuration
user_file_exists configuration || {
  run_as_user <<END
    echo "cloning configuration repo"
    gcloud source repos clone "$epic_lab_repo_configuration"
END
  run_as_user <<'END'
    username=$(cat ~/username)
    if (test -e ~/configuration/$username/alias); then
      echo ". ~/configuration/$username/alias" >> ~/.bashrc
    fi
    if (test -e ~/configuration/$username/ipython_startup.py); then
      ln -s ~/configuration/$username/ipython_startup.py ~/.ipython/profile_default/startup/startup_user.py
    fi
    if (test -e ~/configuration/$username/gitconfig); then
      ln -s ~/configuration/$username/gitconfig ~/.gitconfig
    fi
    if (test -e ~/configuration/$username/jupyterlab-settings); then
      jpl_settings_path="$(~/conda/bin/jupyter lab path | grep -Po '(?<=User Settings directory: )(.*)')"
      mkdir -p "${jpl_settings_path}/@jupyterlab"
      cp -r ~/configuration/$username/jupyterlab-settings/* "${jpl_settings_path}/@jupyterlab/"
    fi
END
}

echo 'epic-lab: checking for "additional_on_create.sh"'

test -f "$RUNDIR/additional_on_create.sh" || {
  fetch_gs_script "additional_on_create.sh" && {
    echo 'epic-lab: running "additional_on_create.sh"'
    "$RUNDIR/additional_on_create.sh"
    echo 'epic-lab: "additional_on_create.sh" done'
  }
}

echo 'epic-lab: on-create script done successfully'
