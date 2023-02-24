import os

import pytest

import epic.lab
from .helpers import patch_gcs_mock, patch_subprocess_mock


@pytest.mark.timeout(10)
def test_synccode(tmp_path):
    with patch_gcs_mock() as gcs_client_mock:
        from epic.lab.synccode import SyncCodeDownloadMonitor

        synccode_path = tmp_path / 'synccode'
        os.makedirs(synccode_path)
        open(synccode_path / "_config", "w").write("bucket=my_bucket\nprefix=my_prefix\n")

        gcs_client_mock.add_blobs('my_bucket')
        gcs_client_mock.add_blobs('unrelated_bucket')

        sdm = SyncCodeDownloadMonitor('user', synccode_path)
        assert sdm.client is not None
        assert sdm.bucket == "my_bucket"
        assert sdm.prefix == "my_prefix"

        sdm.check_for_updates()
        sdm.check_for_updates(wait=True)

        gcs_client_mock.add_blobs(
            'my_bucket',
            'unrelated', b'',
            'my_prefix/some_file', b'',
            'my_prefix/some_folder/some_file', b'',
            'my_prefix/repo01/_synccode_marker', b'',
            'my_prefix/repo01/repo_file', b'',
            'my_prefix/user/some_file', b'',
            'my_prefix/user/some_folder/some_file', b'',
            'my_prefix/user/repo11/_synccode_marker', b'',
            'my_prefix/user/repo11/repo_file1', b'',
            'my_prefix/user/repo12/_synccode_marker', b'',
            'my_prefix/user/repo12/repo_file2', b'',
            'my_prefix/user2/repo21/_synccode_marker', b'',
            'my_prefix/user2/repo21/repo_file', b'',
        )

        sdm = SyncCodeDownloadMonitor('user', synccode_path)
        assert set(sdm.repos) == {'repo11', 'repo12'}
        with pytest.raises(FileNotFoundError, match="synccode uploaded config not found"):
            sdm.check_for_updates()
        gcs_client_mock.add_blobs(
            'my_bucket',
            'my_prefix/user/_config', b'# actual config expected here',
        )
        with patch_subprocess_mock() as mock_check_output:
            sdm.check_for_updates()
            epic_synccode_script = os.path.abspath(os.path.join(
                os.path.dirname(epic.lab.__file__), 'scripts', 'epic-synccode'
            ))
            print(mock_check_output.call_args_list)
            print(list(mock_check_output.call_args_list)[0].args[0])
            call_args = [call.args[0] for call in mock_check_output.call_args_list]
            assert call_args == [
                [epic_synccode_script, "download-repo", "user", "repo11", str(synccode_path / "repo11")],
                [epic_synccode_script, "download-repo", "user", "repo12", str(synccode_path / "repo12")],
            ]
