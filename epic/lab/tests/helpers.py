import subprocess
from contextlib import contextmanager
from unittest.mock import patch, Mock

from google.cloud import storage


class GcsClientMock:
    def __init__(self):
        self.content = {}

    def add_blobs(self, bucket_name, *prefix_data_pairs):
        assert len(prefix_data_pairs) % 2 == 0
        bucket_content = self.content.setdefault(bucket_name, {})
        bucket_content.update({
            prefix: self._blob(prefix, data)
            for prefix, data in zip(prefix_data_pairs[0::2], prefix_data_pairs[1::2])
        })

    def _blob(self, prefix, data):
        blob = Mock(name='MockGcsBlob')
        blob.name = prefix
        blob.data = data
        blob.download_as_bytes.return_value = data
        return blob

    def bucket(self, bucket_name):
        assert bucket_name in self.content
        bucket = Mock(name='MockGcsBucket')
        bucket.name = bucket_name
        bucket.get_blob = lambda path: self.content[bucket_name].get(path)
        return bucket

    def list_blobs(self, bucket, prefix):
        for path, blob in self.content[bucket].items():
            if path.startswith(prefix):
                yield blob


@contextmanager
def patch_gcs_mock():
    with patch("google.cloud.storage") as mock_storage:
        gcs_client_mock = GcsClientMock()
        mock_storage.Client.return_value = gcs_client_mock
        yield gcs_client_mock


@contextmanager
def patch_subprocess_mock():
    with patch("subprocess.check_output") as mock_check_output:
        mock_check_output.return_value = b"mocking a successful execution"
        yield mock_check_output
