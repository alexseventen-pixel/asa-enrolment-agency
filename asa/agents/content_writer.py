"""Content Writer: lesson announcements per program and platform, plus poster copy for both ASA programs."""
from __future__ import annotations

import re

from .. import llm
from ..config import EXPORTS, LESSONS, PROGRAMS, now, ts
from ..db import next_id, session
from ..schedule_utils import next_lesson

PLATFORMS = ["School newsletter", "Facebook", "Instagram", "ManageBac notice"]


def _save(con, platform: str, title: str, body: str, program: str = "") -> str:
    pid = next_id(con, "posts", "post_id", "P-")
    folder = EXPORTS / "posts"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{pid}.md"
    path.write_text(f"# {title}\n\nProgram: {PROGRAMS.get(program, 'Both')}\nPlatform: {platform}\n"
                    f"Status: Draft, waiting for Boss approval\n\n{body}\n")
    con.execute("INSERT INTO posts (post_id, created_at, program, platform, title, body, status, file)"
                " VALUES (?,?,?,?,?,?, 'Draft', ?)",
                (pid, ts(), program or "both", platform, title, body, str(path.relative_to(EXPORTS.parent))))
    return pid


def lesson_posts(con) -> list[str]:
    made = []
    for prog, day in (("AI", "Mon"), ("ZH", "Tue")):
        nl = next_lesson(day, now().date())
        n = nl[0] if nl else 10
        _, title, about = LESSONS[prog][n - 1]
        name = PROGRAMS[prog]
        tags = "#AIClub #AIforKids" if prog == "AI" else "#Chinese #学中文 #ASA"
        for p in PLATFORMS:
            base = {
                "School newsletter": f"This week in {name}, Lesson {n}: {title}. {about} Ask your child what they discovered!",
                "Facebook": f"{name}, Lesson {n}: {title}. {about} {tags} #Premjers",
                "Instagram": f"{name} Lesson {n}: {title}. {about} {tags} #Riga",
                "ManageBac notice": f"{name} reminder: Lesson {n} \"{title}\" takes place this week at the usual group time.",
            }[p]
            body = llm.complete(f"Rewrite for {p}, max 60 words: {base}", base)
            made.append(_save(con, p, f"{name} Lesson {n}: {title}", body, prog))
    return made


def poster(con) -> str:
    ai = "\n".join(f"{n}. {t}" for n, t, _ in LESSONS["AI"])
    zh = "\n".join(f"{n}. {t}" for n, t, _ in LESSONS["ZH"])
    body = ("AFTER-SCHOOL ACTIVITIES AT PREMJERS\nTwo new clubs: AI Club and Chinese\n\n"
            f"AI CLUB (ages 7 to 15), 10 lessons:\n{ai}\n\n"
            f"CHINESE (Beginner to HSK3), 10 lessons:\n{zh}\n\n"
            "Small groups, no clashes if your child joins both.\nRegister with the form link from your class teacher.")
    return _save(con, "Poster", "ASA poster copy: AI Club + Chinese", body, "both")


def freeform(con, text: str) -> list[str]:
    m = re.search(r"(\d+)\s+([A-Za-z]+)\s+posts?\s+(?:about|on)\s+(.+?)(?:,|\.|$| due)", text, re.I)
    count, platform, topic = (int(m.group(1)), m.group(2).capitalize(), m.group(3).strip()) if m else (1, "Facebook", text)
    platform = "LinkedIn" if platform.lower() == "linkedin" else platform
    made = []
    for i in range(1, count + 1):
        base = f"Post {i} of {count} about {topic}: the ASA AI Club helps children aged 7 to 15 learn how AI works by building real projects."
        made.append(_save(con, platform, f"{topic.capitalize()} ({i}/{count})",
                          llm.complete(f"Write post {i}/{count} for {platform} about {topic}, max 60 words.", base)))
    return made


def handle(task: dict) -> dict:
    with session() as con:
        kind = task.get("kind")
        if kind == "poster":
            made = [poster(con)]
        elif kind == "lesson_posts":
            made = lesson_posts(con)
        else:
            made = freeform(con, task.get("task_description", ""))
    return {"status": "Completed", "output": "exports/posts/",
            "note": f"Created {len(made)} draft posts: {', '.join(made)}"}
