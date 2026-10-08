import json
import socket
import time

import pytest

from offspell import instance, paths


@pytest.fixture(autouse=True)
def user_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "user_dir", lambda: str(tmp_path))
    return tmp_path


def wait_for(cond, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return
        time.sleep(0.02)
    raise AssertionError("timed out")


def test_hand_off_reaches_running_window():
    got = []
    server = instance.Server(got.append)
    try:
        assert instance.hand_off({"live": "word"})
        assert instance.hand_off({"path": "C:\\cases\\шийдвэр.docx"})
        wait_for(lambda: len(got) == 2)
        assert got == [{"live": "word"}, {"path": "C:\\cases\\шийдвэр.docx"}]
    finally:
        server.close()
    # the window is gone: the next start must open its own
    assert not instance.hand_off({"live": "word"})


def test_wrong_token_is_refused(user_dir):
    got = []
    server = instance.Server(got.append)
    try:
        info = json.loads((user_dir / "instance.json").read_text(encoding="utf-8"))
        with socket.create_connection(("127.0.0.1", info["port"]), timeout=3) as s:
            s.sendall(b'{"token": "guess", "path": "x.docx"}\n')
            assert s.makefile("rb").readline().strip() == b"denied"
        time.sleep(0.1)
        assert got == []
    finally:
        server.close()


def test_stale_file_from_a_crashed_window(user_dir):
    with socket.socket() as s:     # a port with nobody listening
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    (user_dir / "instance.json").write_text(json.dumps({"port": port, "token": "t", "pid": 1}))
    start = time.time()
    assert not instance.hand_off({})
    assert time.time() - start < 3


def test_unknown_fields_are_dropped():
    got = []
    server = instance.Server(got.append)
    try:
        assert instance.hand_off({"live": "excel", "run": "calc.exe"})
        wait_for(lambda: got)
        assert got == [{"live": "excel"}]
    finally:
        server.close()
