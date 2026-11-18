import json, os, sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DB = os.getenv("SAHAYAK_DB", str(Path(__file__).resolve().parents[1] / "sahayak.db"))
now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.executescript("""
        create table if not exists schemes(id text primary key, data text not null, version int not null, updated_at text not null);
        create table if not exists scheme_history(id text, version int, data text, updated_at text, editor text);
        create table if not exists partners(id text primary key, data text not null, updated_at text not null);
        create table if not exists events(id integer primary key autoincrement, stage text, scheme_id text, ts text);""")
        if c.execute("select count(*) from schemes").fetchone()[0] == 0:
            seed = json.loads((Path(__file__).parent / "seed.json").read_text())
            for s in seed["schemes"]:
                save_scheme(s, "seed", c)
            for p in seed["partners"]:
                p["last_verified"] = (date.today() - timedelta(days=p.pop("verified_days_ago"))).isoformat()
                save_partner(p, c)


def save_scheme(data: dict, editor: str, c=None):
    own = c is None
    c = c or conn()
    row = c.execute("select version from schemes where id=?", (data["id"],)).fetchone()
    v, blob, ts = (row["version"] + 1 if row else 1), json.dumps(data), now()
    c.execute("insert or replace into schemes values(?,?,?,?)", (data["id"], blob, v, ts))
    c.execute("insert into scheme_history values(?,?,?,?,?)", (data["id"], v, blob, ts, editor))
    if own:
        c.commit(); c.close()
    return v


def save_partner(data: dict, c=None):
    own = c is None
    c = c or conn()
    c.execute("insert or replace into partners values(?,?,?)", (data["id"], json.dumps(data), now()))
    if own:
        c.commit(); c.close()


def list_schemes():
    with conn() as c:
        return [{**json.loads(r["data"]), "version": r["version"], "updated_at": r["updated_at"]}
                for r in c.execute("select * from schemes order by id")]


def list_partners():
    with conn() as c:
        return [json.loads(r["data"]) for r in c.execute("select * from partners order by id")]


def history(scheme_id: str):
    with conn() as c:
        return [{"version": r["version"], "updated_at": r["updated_at"], "editor": r["editor"], "data": json.loads(r["data"])}
                for r in c.execute("select * from scheme_history where id=? order by version desc", (scheme_id,))]


def log_event(stage: str, scheme_id: str | None):
    with conn() as c:
        c.execute("insert into events(stage,scheme_id,ts) values(?,?,?)", (stage, scheme_id, now()))


def funnel():
    with conn() as c:
        return {r["stage"]: r["n"] for r in c.execute("select stage, count(*) n from events group by stage")}
