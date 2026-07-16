import datetime

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from data.connection import db_cursor
from data.users import User


@dataclass
class Bloom:
    id: int
    sender: User
    content: str
    sent_timestamp: datetime.datetime
    rebloom_of: Optional[int] = None
    original_sender: Optional[str] = None
    rebloom_count: int = 0


def add_bloom(*, sender: User, content: str) -> Bloom:

    if len(content) > 280:
        raise ValueError(f"Bloom must be 280 characters or fewer.")
     
    hashtags = [word[1:] for word in content.split(" ") if word.startswith("#")]

    now = datetime.datetime.now(tz=datetime.UTC)
    bloom_id = int(now.timestamp() * 1000000)
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO blooms (id, sender_id, content, send_timestamp) VALUES (%(bloom_id)s, %(sender_id)s, %(content)s, %(timestamp)s)",
            dict(
                bloom_id=bloom_id,
                sender_id=sender.id,
                content=content,
                timestamp=datetime.datetime.now(datetime.UTC),
                rebloom_of=None,
            ),
        )
        for hashtag in hashtags:
            cur.execute(
                "INSERT INTO hashtags (hashtag, bloom_id) VALUES (%(hashtag)s, %(bloom_id)s)",
                dict(hashtag=hashtag, bloom_id=bloom_id),
            )


def get_blooms_for_user(
    username: str, *, before: Optional[int] = None, limit: Optional[int] = None
) -> List[Bloom]:
    with db_cursor() as cur:
        kwargs = {
            "sender_username": username,
        }
        if before is not None:
            before_clause = "AND send_timestamp < %(before_limit)s"
            kwargs["before_limit"] = before
        else:
            before_clause = ""

        limit_clause = make_limit_clause(limit, kwargs)

        cur.execute(
            f"""SELECT
              blooms.id, users.username, content, send_timestamp, rebloom_of
            FROM
              blooms INNER JOIN users ON users.id = blooms.sender_id
            WHERE
              username = %(sender_username)s
              {before_clause}
            ORDER BY send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        blooms = []
        for row in rows:
            bloom_id, sender_username, content, timestamp, rebloom_of = row
            blooms.append(
                Bloom(
                    id=bloom_id,
                    sender=sender_username,
                    content=content,
                    sent_timestamp=timestamp,
                    rebloom_of=rebloom_of,
                )
            )
    return blooms


def get_bloom(bloom_id: int) -> Optional[Bloom]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT blooms.id, users.username, content, send_timestamp, rebloom_of FROM blooms INNER JOIN users ON users.id = blooms.sender_id WHERE blooms.id = %s",
            (bloom_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        bloom_id, sender_username, content, timestamp, rebloom_of = row
        return Bloom(
            id=bloom_id,
            sender=sender_username,
            content=content,
            sent_timestamp=timestamp,
            rebloom_of=rebloom_of,
        )


def get_blooms_with_hashtag(
    hashtag_without_leading_hash: str, *, limit: int = None
) -> List[Bloom]:
    kwargs = {
        "hashtag_without_leading_hash": hashtag_without_leading_hash,
    }
    limit_clause = make_limit_clause(limit, kwargs)
    with db_cursor() as cur:
        cur.execute(
            f"""SELECT
              blooms.id, users.username, content, send_timestamp, rebloom_of
            FROM
              blooms 
              INNER JOIN hashtags ON blooms.id = hashtags.bloom_id 
              INNER JOIN users ON blooms.sender_id = users.id
            WHERE
              hashtag = %(hashtag_without_leading_hash)s
            ORDER BY send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        blooms = []
        for row in rows:
            bloom_id, sender_username, content, timestamp, rebloom_of = row
            blooms.append(
                Bloom(
                    id=bloom_id,
                    sender=sender_username,
                    content=content,
                    sent_timestamp=timestamp,
                    rebloom_of=rebloom_of,
                )
            )
    return blooms

def get_all_blooms(limit=50):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT
                blooms.id,
                users.username,
                content,
                send_timestamp,
                rebloom_of
            FROM blooms
            INNER JOIN users ON users.id = blooms.sender_id
            ORDER BY send_timestamp DESC
            LIMIT %(limit)s
            """,
            {"limit": limit},
        )

        rows = cur.fetchall()

    return [
        Bloom(
            id=row[0],
            sender=row[1],
            content=row[2],
            sent_timestamp=row[3],
            rebloom_of=row[4],
        )
        for row in rows
    ]


def make_limit_clause(limit: Optional[int], kwargs: Dict[Any, Any]) -> str:
    if limit is not None:
        limit_clause = "LIMIT %(limit)s"
        kwargs["limit"] = limit
    else:
        limit_clause = ""
    return limit_clause

def add_rebloom(*, sender: User, bloom_id: int) -> Bloom:
    now = datetime.datetime.now(datetime.UTC)
    new_id = int(now.timestamp() * 1000000)

    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO blooms
            (id, sender_id, content, send_timestamp, rebloom_of)
            SELECT
                %(new_id)s,
                %(sender_id)s,
                content,
                %(timestamp)s,
                id
            FROM blooms
            WHERE id=%(bloom_id)s
            RETURNING id, content, send_timestamp, rebloom_of
            """,
            {
                "new_id": new_id,
                "sender_id": sender.id,
                "timestamp": now,
                "bloom_id": bloom_id,
            },
        )

        row = cur.fetchone()

    if row is None:
        raise ValueError(f"Bloom with id {bloom_id} does not exist.")

    return Bloom(
        id=row[0],
        sender=sender.username,
        content=row[1],
        sent_timestamp=row[2],
        rebloom_of=row[3],
    )