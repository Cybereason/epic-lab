import os
import sys
import time
import subprocess

from google.cloud import storage

CLOUD_SYNCCODE_BASE_DIR = os.path.expanduser("~/synccode")
SYNCCODE_SUB_PATHS_FN = ".synccode_sub_paths"


class SyncCodeDownloadMonitor:
    SYNCCODE_MARKER = '_synccode_marker'
    UPLOADED_CONFIG = '_config'

    def __init__(self, user=None, local_target_path=None, verbose=True):
        self.client = storage.Client()
        if user is None:
            user = open(os.path.expanduser("~/username"), "r").read().strip()
        self.user = user
        if local_target_path is None:
            local_target_path = CLOUD_SYNCCODE_BASE_DIR
        self.local_target_path = local_target_path
        self.bucket = None
        self.prefix = None
        for line in filter(bool, open(os.path.join(self.local_target_path, "_config")).read().split("\n")):
            if line.startswith("bucket="):
                self.bucket = line.split("=", 1)[1]
            elif line.startswith("prefix="):
                self.prefix = line.split("=", 1)[1]
        assert self.bucket is not None, "missing 'bucket=...' configuration"
        assert self.prefix is not None, "missing 'prefix=...' configuration"
        self.repos = self._discover_repos()
        self.verbose = verbose
        self.synccode_bucket = self.client.bucket(self.bucket)
        self._marker_blobs_updated = {}

    def _discover_repos(self):
        repos = []
        prefix = f'{self.prefix}/{self.user}/'
        # note: this iterates every file in every repo, we could speed this up
        for blob in self.client.list_blobs(self.bucket, prefix=prefix):
            subkey = blob.name.split(prefix, 1)[1]
            if subkey.count("/") == 1 and subkey.endswith(f"/{self.SYNCCODE_MARKER}"):
                repos.append(subkey.split("/")[0])
        return repos

    def check_for_updates(self, wait=False):
        if not self.repos:
            print(f"warning: no repos found for user {self.user}, upload some or restart this kernel")
            return
        while True:
            # download the latest config for scripts reference
            config_text = self._get_config_text()
            open(os.path.join(self.local_target_path, "_uploader_config"), "w").write(config_text)
            # note: this can be parallelized
            repos_to_update = [repo for repo in self.repos if self._should_update(repo)]
            if not repos_to_update:
                if wait:
                    time.sleep(1)
                    continue
                return
            print(f"downloading synccode changes for {', '.join(repos_to_update)}")
            for repo in repos_to_update:
                print(f"update detected for repo {repo}")
                self.download(repo)
            print(f"all synccode changes downloaded successfully")
            return

    def download(self, repo):
        synccode_sh_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "scripts", "epic-synccode"))
        cmd = [synccode_sh_path, 'download-repo', self.user, repo, self._local_path(repo)]
        try:
            output = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                env={
                    # note: since we're passing the PATH variable, we might not need PYTHON_EXECUTABLE anymore
                    'HOME': os.getenv("HOME"),
                    'PATH': os.getenv("PATH"),
                    'PYTHON_EXECUTABLE': sys.executable,
                }
            )
        except subprocess.CalledProcessError as exc:
            print(
                f"Error raised from running synccode download command:\n{cmd}\n---\n"
                f"{exc.output.decode('ascii', errors='replace')}",
                file=sys.stderr
            )
            raise Exception(f"failed to download changes from synccode") from None
        else:
            if self.verbose:
                print(output.decode("ascii", errors='replace'))
        self._marker_blobs_updated[repo] = self._get_marker_blob(repo).updated

    def _should_update(self, repo):
        if repo in self._marker_blobs_updated:
            # check for a newer updated on the marker (faster)
            updated = self._get_marker_blob(repo).updated
            if updated == self._marker_blobs_updated[repo]:
                return False
        # check for different content of the marker
        # this is slightly slower, but
        # (a) it is needed on first run and
        # (b) it can prevent an update when download already happened elsewhere
        return self._marker_content_changed(repo)

    def _marker_content_changed(self, repo):
        marker_path = f"{self._local_path(repo)}/{self.SYNCCODE_MARKER}"
        return (
            not os.path.exists(marker_path) or
            open(marker_path, "rb").read() != self._get_marker_blob(repo).download_as_bytes()
        )

    def _local_path(self, repo):
        return os.path.join(self.local_target_path, repo)

    def _get_marker_blob(self, repo):
        blob = self.synccode_bucket.get_blob(f'{self.prefix}/{self.user}/{repo}/{self.SYNCCODE_MARKER}')
        if blob is None:
            raise FileNotFoundError(
                f"synccode repo {repo} not found for user {self.user} or is mal-formatted (metadata marker missing)"
            )
        return blob

    def _get_config_text(self):
        blob = self.synccode_bucket.get_blob(f'{self.prefix}/{self.user}/{self.UPLOADED_CONFIG}')
        if blob is None:
            raise FileNotFoundError(
                f"synccode uploaded config not found for user {self.user}"
            )
        return blob.download_as_bytes().decode("ascii").replace("\r\n", "\n")


def setup_synccode_path(repos=None):
    if repos is None:
        repos = [
            fn for fn in os.listdir(CLOUD_SYNCCODE_BASE_DIR)
            if os.path.isdir(os.path.join(CLOUD_SYNCCODE_BASE_DIR, fn))
        ]
    for repo in repos:
        repo_path = os.path.join(CLOUD_SYNCCODE_BASE_DIR, repo)
        sub_paths = ["."] if not os.path.exists(fn := os.path.join(repo_path, SYNCCODE_SUB_PATHS_FN)) else (
            filter(bool, map(str.strip, open(fn, "r").read().split("\n")))
        )
        paths = [
            repo_path if sub_path == "." else os.path.join(repo_path, sub_path)
            for sub_path in sub_paths
        ]
        for path in paths:
            if os.path.exists(path) and path not in sys.path:
                sys.path.append(path)
