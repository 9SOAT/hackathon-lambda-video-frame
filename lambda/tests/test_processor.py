import json
import logging
import os
import subprocess
import zipfile
import sys

import pytest

# PYTHONPATH para importar lambda_processor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lambda')))

import lambda_processor as lp


def test_download_from_s3_monkeypatched(monkeypatch, tmp_path):
    called = {}

    def fake_download_file(bucket, key, dest):
        called['bucket'] = bucket
        called['key'] = key
        called['dest'] = dest
        # cria arquivo para simular download
        open(dest, 'wb').close()

    monkeypatch.setattr(lp.s3_client, 'download_file', fake_download_file)

    bucket = 'input-bucket'
    key = 'video.mp4'
    job_id = 'job123'
    timestamp = '1750686751'

    returned = lp.download_from_s3(bucket, key, job_id, timestamp)

    expected = f"/tmp/{job_id}_{timestamp}.mp4"
    assert returned == expected
    assert called == {'bucket': bucket, 'key': key, 'dest': expected}
    assert os.path.exists(returned)


def test_create_zip_and_contents(tmp_path):
    frames_dir = tmp_path / "frames_test"
    frames_dir.mkdir()

    filenames = ['a.jpg', 'b.jpg', 'c.jpg']
    for fname in filenames:
        (frames_dir / fname).write_bytes(b'data')

    job_id = 'job123'
    timestamp = '1750686751'
    zip_path = lp.create_zip(str(frames_dir), job_id, timestamp)

    assert os.path.isfile(zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = zf.namelist()
    assert set(names) == set(filenames)


def test_upload_to_s3_monkeypatched(monkeypatch):
    called = {}

    def fake_upload_file(file_path, bucket, key):
        called['file_path'] = file_path
        called['bucket'] = bucket
        called['key'] = key

    monkeypatch.setattr(lp.s3_client, 'upload_file', fake_upload_file)

    path = '/tmp/test.zip'
    bucket = 'output-bucket'
    key = 'job123.zip'
    lp.upload_to_s3(path, bucket, key)

    assert called == {'file_path': path, 'bucket': bucket, 'key': key}


def test_update_metadata(monkeypatch):
    captured = {}

    class DummyTable:
        def put_item(self, Item):
            captured['Item'] = Item

    monkeypatch.setattr(lp.dynamodb, 'Table', lambda name: DummyTable())

    lp.update_metadata('job123', 'in.mp4', 'out.zip')

    item = captured['Item']
    assert item['user_prefix'] == 'job123'
    assert item['input_key'] == 'in.mp4'
    assert item['output_key'] == 'out.zip'
    assert item['status'] == 'COMPLETED'


def test_publish_notification(monkeypatch):
    captured = {}

    def fake_publish(TopicArn, Message, Subject):
        captured['TopicArn'] = TopicArn
        captured['Message'] = json.loads(Message)
        captured['Subject'] = Subject

    monkeypatch.setattr(lp.sns_client, 'publish', fake_publish)

    lp.publish_notification('job123', '1750686751', 'job123.zip')

    assert captured['TopicArn'] == lp.SNS_TOPIC_ARN
    assert 'job123.zip' in captured['Message']['download_url']
    assert 'job123' in captured['Subject']


def test_extract_frames_success(monkeypatch, tmp_path):
    captured = {}

    def fake_run(cmd, check):
        captured['cmd'] = cmd
        out_dir = os.path.dirname(cmd[-1])
        os.makedirs(out_dir, exist_ok=True)
        for i in range(1, 4):
            open(os.path.join(out_dir, f'frame_{i:04d}.jpg'), 'wb').close()

    monkeypatch.setattr(subprocess, 'run', fake_run)

    video = tmp_path / "video.mp4"
    video.write_bytes(b"")

    prefix = "job123"
    timestamp = "T1"
    out_dir = lp.extract_frames(str(video), prefix, timestamp)

    assert os.path.isdir(out_dir)
    assert out_dir.endswith(f"frames_{prefix}_{timestamp}")

    expected_cmd = [
        lp.FFMPEG_BIN,
        "-i",
        str(video),
        "-vf",
        "fps=1",
        f"{out_dir}/frame_%04d.jpg",
    ]
    assert captured['cmd'] == expected_cmd

    files = os.listdir(out_dir)
    assert any(name.startswith("frame_") and name.endswith(".jpg") for name in files)


def test_extract_frames_failure(monkeypatch, tmp_path):
    def fake_run(cmd, check):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(subprocess, 'run', fake_run)

    video = tmp_path / "video.mp4"
    video.write_bytes(b"")

    with pytest.raises(subprocess.CalledProcessError):
        lp.extract_frames(str(video), "jobX", "tsX")


def test_lambda_handler_calls_process_message(monkeypatch):
    event = {"Records": [{"body": "first"}, {"body": "second"}]}
    called = []

    def fake_process_message(record):
        called.append(record["body"])

    monkeypatch.setattr(lp, "process_message", fake_process_message)

    result = lp.lambda_handler(event, context=None)

    assert called == ["first", "second"]
    assert result is None


def test_lambda_handler_handles_exception(monkeypatch, caplog):
    event = {"Records": [{"body": "bad"}]}

    def fake_process_message(record):
        raise RuntimeError("fail")

    monkeypatch.setattr(lp, "process_message", fake_process_message)
    caplog.set_level(logging.ERROR)

    assert lp.lambda_handler(event, context=None) is None

    error_messages = [rec.message for rec in caplog.records if rec.levelno == logging.ERROR]
    assert any("fail" in msg for msg in error_messages)
