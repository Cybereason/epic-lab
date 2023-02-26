# Epic lab :: cloud setup

The setup process is made up of three parts.
Each part provides an additional layer of value for your setup, and relies on the previous ones.
You don't have to implement all of them - in fact you get most of the value (notebook machines and synccode) just from
the first part, which is also the simplest to set up.

The three parts are:
1. setting up cloud resources to allow launching notebook VM instances and synchronizing working code into them
2. setting up a reverse proxy to allow accessing the VMs through one base URL and the VM's name
3. setting up secure access from the Internet to the reverse proxy based on GCP authentication and access management

## Setting up the basic lab resources

The following is a run through of the steps you'll need to run. Use it as a base template and adapt for your specific
needs. It is recommended to run the commands one by one and review each command's output for potential errors.

First, clone this repository.

Then, run the following commands in its root folder:

```shell
# basic configuration - replace with your choice of values
project_id="epic-lab-123456"
region="us-central1"
zone="${region}-a"
# when creating local configuration and launching the first notebook, we'll use this username (must not include hyphens)
your_username="gooduser"
# override these if you don't like the default
bucket="$project_id"
ssh_key_name="$project_id"

project_number=$(gcloud projects list --filter="$project_id" --format="value(PROJECT_NUMBER)")
default_service_account="${project_number}-compute@developer.gserviceaccount.com"

# the generated keys will allow you to ssh into the VM, as well as to ssh from one VM to another.
# they will also be automatically deployed onto each VM's ~/.ssh folder.
ssh-keygen -f "$ssh_key_name"

# TODO: create a notebook password hash file using some variation of jupyter notebook password.
# take care though because just running `jupyter notebook password` overrides your local notebook configuration.
jupyter_password_hash_file="jupyter_password_hash.json"

# enable services
# note: this change sometimes takes a few minutes to propagate
gcloud --project "$project_id" services enable compute.googleapis.com
gcloud --project "$project_id" services enable secretmanager.googleapis.com
gcloud --project "$project_id" services enable sourcerepo.googleapis.com

# grant editor permissions to the default service account
gcloud --project "$project_id" projects add-iam-policy-binding "$project_id" \
    --member="serviceAccount:$default_service_account" --role='roles/editor'
# grant secret manager permissions to epic-lab secrets
gcloud --project "$project_id" projects add-iam-policy-binding "$project_id" \
    --member="serviceAccount:$default_service_account" --role='roles/secretmanager.secretAccessor' \
    --condition="expression=resource.name.startsWith(\"projects/$project_number/secrets/epic-lab-\"),title=epic-lab-secrets-only,description=epic-lab-secrets-only"

# create secrets
gcloud --project "$project_id" secrets create --replication-policy="automatic" epic-lab-ssh-key-private
gcloud --project "$project_id" secrets versions add epic-lab-ssh-key-private --data-file="$ssh_key_name"
gcloud --project "$project_id" secrets create --replication-policy="automatic" epic-lab-ssh-key-public
gcloud --project "$project_id" secrets versions add epic-lab-ssh-key-public --data-file="$ssh_key_name.pub"
gcloud --project "$project_id" secrets create --replication-policy="automatic" epic-lab-jupyter-password
gcloud --project "$project_id" secrets versions add epic-lab-jupyter-password --data-file="$jupyter_password_hash_file"

# create gcp repos
gcloud --project "$project_id" source repos create notebooks
gcloud --project "$project_id" source repos create configuration

# create bucket for scripts and synccode
gcloud --project "$project_id" storage buckets create "gs://$bucket"
```

We now have all the core cloud resources we need for our environment.

Next, we'll create a versioned VM setup deployment. We will:
1. Upload the core VM setup scripts to a folder with our version name
2. Create a config file to reflect its parameters
3. Optionally, upload externally provided additional setup scripts

This part can be repeated whenever a new modified version of the setup scripts needs to be deployed. Old versions can
continue to be used as long as the user configuration keeps reflecting the older version. Cloud VMs are not upgradeable. 

Run these commands in continuation to the previous section (i.e. with the same environment variables):

```shell
# this will be the version of our deployed VM setup scripts
vm_setup_version="vmsetup_$(date +%Y%m%d)"

# upload core VM setup scripts
gcloud --project "$project_id" storage cp vmsetup/** "gs://$bucket/$vm_setup_version"

# OPTIONAL: you can upload additional scripts to further setup your VM beyond the standard epic-lab scripts.
# A file named "additional_on_create.sh" is executed once when the machine has completed its initial setup.
# Other files can be uploaded to the folder as well, and used by the "additional_on_create" script.
# for example:
test -f additional_on_create.sh && \
  gcloud --project "$project_id" storage cp additional_on_create.sh "gs://$bucket/$vm_setup_version/"

# prepare config
# note: change values here as relevant
mkdir -p ~/.epic
cat << EOF > ~/.epic/lab
# general configuration
GCP_PROJECT_ID=$project_id
GCP_GCS_SCRIPTS_BASE_PATH=gs://$bucket/$vm_setup_version
GCP_ZONE=$zone

# synccode
# warning: don't change the base url - it currently MUST be at the base of the scripts bucket in a 'synccode' folder
SYNCCODE_GCS_BASE_URL=gs://$bucket/synccode
SYNCCODE_USERNAME=$your_username
SYNCCODE_LOCAL_CODE_BASE=~/code
SYNCCODE_REPOS=my-project,my-other-project
# SYNCCODE_EXCLUSION=... (optional - override default exclusion)
EOF
```

The setup is ready to start working, and your local machine is configured to work with it.

The next step is to launch the first VM instance.
This can be done now on any local machine and for any user, as long as they have the proper configuration.

For the sake of example, we'll continue to launch for the same user we've run from until now.

```shell
# launch your first machine
# note: if you didn't `pip install` the epic-lab library, you can still run the scripts directly from 'epic/lab/scripts'
notebook_instance_name="$your_username-$(date +%Y%m%d)"
epic-notebook launch "$notebook_instance_name"

# follow the logs and make sure that installation went well.
# look for the line "epic-lab: on-create script done successfully" when the process is done.
epic-notebook logs "$notebook_instance_name"
```

## Setting up a reverse proxy using Cloud Run

First, go and read a bit about the proxy in [proxy/README.md](proxy/README.md).

Use the commands below to build and deploy a proxy container into the Cloud Run service.

> Note:
>
> The proxy container created in this section will NOT be accessible from the Internet.
> You will have to configure secure access in a follow-up step.
>
> See the "IAP proxy to cloud run" section below for a suggestion of how to do that using IAP, a domain, a certificate
> and a dedicated HTTPS load balancer.

Run these commands in continuation to those of the previous section:

```shell
# configuration: these defaults should usually work out of the box
vpc_network_name=default
available_ip_range_28="10.8.0.0/28"

cd proxy

# note: this change sometimes takes a few minutes to propagate
gcloud --project "$project_id" services enable cloudbuild.googleapis.com
gcloud --project "$project_id" services enable run.googleapis.com
gcloud --project "$project_id" services enable vpcaccess.googleapis.com

# create a connector to the default VPC using an unused IP address range 10.8.0.0/28
gcloud --project "$project_id" compute networks vpc-access connectors create epic-lab-proxy \
  --network="$vpc_network_name" \
  --region=$region \
  --range="$available_ip_range_28"
# verify readiness
gcloud --project "$project_id" compute networks vpc-access connectors describe epic-lab-proxy \
  --region=$region \
  | grep 'state: READY'

# create cloudbuild.yaml
# note: if you want to provide PUBLIC_BASE_URL as well, add another build arg. see proxy/README.md for details.
echo "
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: [
    'build', '-t', 'gcr.io/$project_id/epic-lab-proxy', '.',
    '--build-arg', 'GCP_PROJECT_NAME=$project_id',
  ]
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'gcr.io/$project_id/epic-lab-proxy']
" > ./cloudbuild.yaml

gcloud --project "$project_id" builds submit

# note: we allow unauthenticated access but only from internal sources and cloud load balancing.
#       this is the only way to enable IAP and HTTPS load balancer.
gcloud --project "$project_id" run deploy epic-lab-proxy \
  --image "gcr.io/$project_id/epic-lab-proxy" \
  --platform=managed \
  --port 80 \
  --region=$region \
  --vpc-connector=epic-lab-proxy \
  --allow-unauthenticated \
  --ingress=internal-and-cloud-load-balancing
epic_lab_proxy_cloud_run_url=$(gcloud --project "$project_id" run services describe epic-lab-proxy \
  --region $region \
  --format="get(status.url)")
```

To test the service, run something like this:
```shell
# parameters
gcp_user_email=your_email@example.com
notebook_instance_name=gooduser-20220704

gcloud --project "$project_id" run services add-iam-policy-binding epic-lab-proxy \
  --member="user:$gcp_user_email" \
  --role='roles/run.invoker' \
  --region=$region
curl -L -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$epic_lab_proxy_cloud_run_url/$notebook_instance_name"
```

## Setting up secure access using IAP

This part of the setup is roughly based on
[this guide](https://medium.com/google-cloud/cloud-iap-on-cloud-run-2b97ee9cd47a).
It is recommended to read through it first, so you have a sense of what we're doing here - the setup process is somewhat
elaborate.

Before getting started, you will need a [Google-managed domain](https://domains.google/) and a
[Cloud DNS zone](https://console.cloud.google.com/net-services/dns/zones) associated with it.
We'll use this domain as the base url for every notebook instance.
You can either use your registered domain or a subdomain, so for example you could use `lab.my-project.io`, resulting in
notebooks accessible via `https://lab.my-project.io/gooduser-20220704`.

Configure the parameters below to get started. It is okay that the DNS zone be managed in another GCP project.
```shell
# parameters
epic_lab_proxy_domain="my-epic-lab.io"
dns_zone_name="my-epic-lab-io"
dns_project_id="$project_id"
```

Now, follow these steps carefully:
```shell
# allocate a public static ip
gcloud --project "$project_id" compute addresses create epic-lab-proxy \
  --network-tier=PREMIUM \
  --global \
  --ip-version=IPV4
epic_lab_proxy_ipaddr=$(gcloud --project "$project_id" compute addresses describe epic-lab-proxy \
  --format="get(address)" \
  --global)

# These three are prep for IAP, not the load balancer; but setting up a DNS takes time.
# create a DNS A record
gcloud --project "$dns_project_id" dns record-sets create "$epic_lab_proxy_domain" \
  --zone="$dns_zone_name" \
  --type="A" \
  --ttl="300" \
  --rrdatas="$epic_lab_proxy_ipaddr"
# create an SSL certificate
gcloud --project "$project_id" compute ssl-certificates create epic-lab-proxy \
  --description="epic-lab-proxy" \
  --domains="$epic_lab_proxy_domain" \
  --global
# check its status - should be PROVISIONING, and it should remain at that state until we're fully set up
gcloud --project "$project_id" compute ssl-certificates describe epic-lab-proxy \
  --global \
  --format="get(name,managed.status,managed.domainStatus)"

# create and configure a load balancer and all its sub-components (NEG, backend service, target proxy, forwarding rule)
gcloud --project "$project_id" compute network-endpoint-groups create epic-lab-proxy \
  --region=$region \
  --network-endpoint-type=serverless  \
  --cloud-run-service=epic-lab-proxy
gcloud --project "$project_id" compute backend-services create epic-lab-proxy \
  --load-balancing-scheme=EXTERNAL \
  --global
gcloud --project "$project_id" compute backend-services add-backend epic-lab-proxy \
  --global \
  --network-endpoint-group=epic-lab-proxy \
  --network-endpoint-group-region=$region
gcloud --project "$project_id" compute url-maps create epic-lab-proxy \
   --default-service epic-lab-proxy
gcloud --project "$project_id" compute target-https-proxies create epic-lab-proxy \
  --ssl-certificates=epic-lab-proxy \
  --url-map=epic-lab-proxy
gcloud --project "$project_id" compute forwarding-rules create epic-lab-proxy \
  --load-balancing-scheme=EXTERNAL \
  --network-tier=PREMIUM \
  --address=epic-lab-proxy \
  --target-https-proxy=epic-lab-proxy \
  --global \
  --ports=443


# set up IAP
gcloud --project "$project_id" services enable iap.googleapis.com
# create an OAuth brand (also known as a "consent screen")
gcloud --project "$project_id" iap oauth-brands create \
  --application_title=epic-lab-proxy \
  --support_email="$gcp_user_email"
epic_lab_proxy_brand=$(gcloud --project=$project_id iap oauth-brands list \
  --filter="applicationTitle=epic-lab-proxy" \
  --format="get(name)")
# create an OAuth client
gcloud --project "$project_id" iap oauth-clients create "$epic_lab_proxy_brand" \
  --display_name=epic-lab-proxy
epic_lab_proxy_oauth_client_secret=$(gcloud --project=$project_id iap oauth-clients list "$epic_lab_proxy_brand" \
  --filter="displayName=epic-lab-proxy" \
  --format="get(secret)")
epic_lab_proxy_oauth_client_id=$(gcloud --project=$project_id iap oauth-clients list "$epic_lab_proxy_brand" \
  --filter="displayName=epic-lab-proxy" \
  --format="get(name.basename())" \
  | grep -Eo '[^/]+$')
# create an identity service account for IAP (only created if it doesn't exist yet)
gcloud --project "$project_id" beta services identity create \
  --service=iap.googleapis.com \
  --project=$project_id
# modify the load balancer backend service to use IAP
gcloud --project "$project_id" compute backend-services update epic-lab-proxy \
  --global \
  --iap="enabled,oauth2-client-id=$epic_lab_proxy_oauth_client_id,oauth2-client-secret=$epic_lab_proxy_oauth_client_secret"

# wait until the certificate status becomes AVAILABLE.
# this could take (in theory) up to 72 hours until DNS changes propagate, but in practice, it takes 10-15 minutes.
gcloud --project "$project_id" compute ssl-certificates describe epic-lab-proxy \
  --global \
  --format="get(name,managed.status,managed.domainStatus)"
```

The final step is to assign IAP privileges to any user or group who should be able to access the lab environment.
* Go here: https://console.cloud.google.com/security/iap
* Click the "epic-lab-proxy" / "Global HTTP(S) Load Balancer" row
* Click "Add Principal"
* Enter the user or group principals and grant "Cloud IAP -> IAP-secured Web App User"

Please note that it takes several minutes before the privilege is propagated.

# 🧑‍🔬 Rejoice and go do lab things! 🔬

You can now access your notebook securely using a URL such as the following:
> `https://my-epic-lab.io/gooduser-20220704`
