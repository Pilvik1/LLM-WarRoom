from backend import storage


def test_conversation_persists_and_lists(tmp_path, monkeypatch):
    data_dir = tmp_path / "conversations"
    monkeypatch.setattr(storage, "DATA_DIR", str(data_dir))

    created = storage.create_conversation("conversation-1")
    storage.add_user_message(created["id"], "hello")

    restored = storage.get_conversation(created["id"])
    assert restored is not None
    assert restored["messages"] == [{"role": "user", "content": "hello"}]
    assert storage.list_conversations()[0]["message_count"] == 1


def test_conversation_id_cannot_escape_data_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path / "conversations"))
    assert storage.get_conversation("../../outside") is None
