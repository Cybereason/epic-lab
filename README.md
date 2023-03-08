# Epic lab &mdash; Opinionated research lab management tools
[![Epic-lab CI](https://github.com/Cybereason/epic-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/Cybereason/epic-lab/actions/workflows/ci.yml)

## What is it?

The **epic-lab** Python library and its additional resources serve to create a fully functional cloud lab environment
for organizational &mdash; or individual &mdash; research work.

## An opinionated library

This library makes specific choices in several major questions, not leaving them open for configuration.

It currently holds the following non-negotiable opinions:
* Uses Google Cloud Platform
* Uses compute VM instances which...
  * are for individual usage
  * are named `username-<suffix>` (launch date suffix recommended)
  * run on Ubuntu 20.04 LTS
  * use Python 3.10
  * use [conda](https://docs.conda.io/en/latest/index.html) for Python environment management
  * run [Jupyter Lab](https://jupyter.org/)
  * come pre-installed with some tools with pinned versions
    * `gcc-10, nodejs v16`
  * come pre-installed with some Python libraries with mostly pinned versions
    * `numpy, pandas, matplotlib, scikit-learn, cython, pybind11, networkx, lz4, tqdm, dill, cytoolz`
  * come pre-installed with the core epic-framework libraries
  * protect against OOM crashes by limiting Jupyter Lab service memory usage (85% soft, 92% hard)
* Uses shared cloud resources:
  * One GCP project for everything
  * A shared GCP git repository for notebook storage
  * A shared GCP git repository for user configuration storage
  * A shared service account (the project's default) for VMs
* Code is...
  * developed on a local machine
  * uploaded to a shared staging area
  * downloaded on VMS for usage
  * auto-downloaded whenever an IPython kernel is started

It also strongly encourages you to:
* Use a single Cloud Run NGINX reverse proxy to access notebooks via  
  `https://<common-domain>/<instance-name>`
* Use a single Google-managed domain for your base url
* Limit online access through GCP authentication and access management (using IAP on a Load Balancer)

Future major releases would likely update some of these opinions, most commonly by updating versions where applicable.

## Alternative opinions welcome

All other opinions are just a fork away!

While this project does not offer many formalized ways to parameterize its behavior, it does allow anyone to fork it and
modify any areas of the setup code to fit their specific needs. Every lab environment is different and so it is expected
to happen often. This is especially true for the `vmsetup` and `proxy` areas.

The `epic-lab` Python library is somewhat more generic, and should hopefully be usable as-is for most situations. If it
isn't, we would certainly appreciate getting a pull request.

## Usage

### Preparation

Typical users of an epic lab environment need to do two things:
1. install the `epic-lab` library
2. create a configuration file at `~/.epic/lab`

This of course assumes that a cloud lab has been set up. See the [Cloud setup guide](#cloud-setup-guide) section below
for details. This is a process that only needs to be done once.
Use the `~/.epic/lab` configuration created during this setup process as a template for providing general users with
their own derivative configuration files.

### Working with a notebook instance

To launch a new VM, run the `epic-notebook launch` command. For example:
```shell
epic-notebook launch gooduser-20220704 n2-standard-2
```

To suspend a VM, run the `epic-notebook suspend` command. For example:
```shell
epic-notebook suspend gooduser-20220704
```

To resume a suspended VM, run the `epic-notebook resume` command. For example:
```shell
epic-notebook resume gooduser-20220704
```

To terminate a VM, run the `epic-notebook terminate` command. For example:
```shell
epic-notebook terminate gooduser-20220704
```

To connect to the machine using `ssh`, run the `epic-notebook ssh` command.
This does not use a direct network connection, tunneling through the IAP service instead.
This requires users to have the following IAM roles assigned to them:
* `roles/iap.tunnelResourceAccessor`
* `roles/compute.instanceAdmin.v1`

Note that any additional arguments will be passed to `ssh`. So you can use it to e.g. forward a port by running:
```shell
epic-notebook ssh gooduser-20220704 -L 18080:localhost:8080
```

### Synchronizing working code into VMs

Code synchronization works through a shared staging area. Repositories (really, folders) under a common parent directory
are _uploaded_ to the staging area from the local working machine, and then later downloaded to a shared parent
directory (`~/synccode`) on cloud VMs for usage.

To upload all changes to synchronized repos **from your local** working machine, run the `epic-synccode upload` command.

You can optionally give it one or more repos as parameters to upload their changes exclusively.
For example:
```shell
epic-synccode upload repo1,repo2,repo3
```

To download all changes **on your cloud VM**, run the `epic-synccode download` command.

> Note: The `epic-synccode download` runs implicitly whenever an IPython kernel is started.

If you want to stop synchronizing a previously synchronized repo, start by running **on your local** working machine
the `epic-synccode delete` command. For example:
```shell
epic-synccode delete repo2
```

After this command, VM downloaded copies of `repo2` will not be updated further, but are not auto-deleted. Remove these
copies from e.g. `~/synccode/repo2` manually.

Finally, if you want to load all synccode paths into your python path, you can use the `epic-synccode path` command.
This is useful for running modules with `python -m`. For example:
```shell
PYTHONPATH=$(epic-synccode path) python -m repo.pkg.module
```

## Cloud setup guide

The setup process is made up of three parts.
Each part provides an additional layer of value for your setup, and relies on the previous ones.
You don't have to implement all of them - in fact you get most of the value (notebook machines and synccode) just from
the first part, which is also the simplest to set up.

The three parts are:
1. setting up cloud resources to allow launching notebook VM instances and synchronizing working code into them
2. setting up a reverse proxy to allow accessing the VMs through one base URL and the VM's name
3. setting up secure access from the Internet to the reverse proxy based on GCP authentication and access management

Follow the full guide in [cloud_setup.md](cloud_setup.md) to create your lab today.
