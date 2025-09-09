import io, json, os, time
from importlib.machinery import SourceFileLoader

APP_PATH = os.path.abspath("app.py")
root_app = SourceFileLoader("root_app", APP_PATH).load_module()
app = root_app.app

def test_mom_q_add_list_clear(tmp_path, monkeypatch):
    # isolate storage
    qfile = tmp_path / "mom_questions.json"
    monkeypatch.setattr(root_app, "MOM_Q_FILE", qfile, raising=True)

    client = app.test_client()

    # start empty
    r = client.get("/mom/q/list")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("ok") is True
    assert int(body.get("count", -1)) == 0

    # add two questions
    r1 = client.post("/mom/q/add", json={"text": "What was your first job?"})
    r2 = client.post("/mom/q/add", json={"text": "Who inspired you most as a child?"})
    assert r1.status_code == 200 and r2.status_code == 200

    b1 = r1.get_json(); b2 = r2.get_json()
    assert b1.get("ok") and b2.get("ok")
    assert isinstance(b1["data"]["id"], str)
    assert isinstance(b2["data"]["id"], str)

    # list: should show 2
    rlist = client.get("/mom/q/list")
    assert rlist.status_code == 200
    L = rlist.get_json()
    assert L.get("ok") is True
    assert int(L.get("count")) == 2
    texts = [i.get("text") for i in L.get("items", [])]
    assert "What was your first job?" in texts
    assert "Who inspired you most as a child?" in texts

    # clear
    rc = client.post("/mom/q/clear")
    assert rc.status_code == 200
    assert rc.get_json().get("ok") is True

    # list again -> 0
    rlist2 = client.get("/mom/q/list")
    assert rlist2.status_code == 200
    assert int(rlist2.get_json().get("count")) == 0