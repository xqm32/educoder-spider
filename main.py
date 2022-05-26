import json
import logging
import os

import httpx
import maya
from rich import print
from rich.columns import Columns
from rich.logging import RichHandler
from rich.progress import Progress
from rich.prompt import Prompt
from rich.traceback import install
from rich.table import Table
from rich import box

install()

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger("rich")


class EduCoder:
    def __init__(self):
        if os.path.exists("config.json"):
            with open("config.json") as f:
                config = json.load(f)
        else:
            username = Prompt.ask("Username")
            password = Prompt.ask("Password", password=True)
            config = {"login": username, "password": password}

        print(f'Read config of {config["login"]}')

        self.client = httpx.Client(proxies={"all://": None})
        self.client.post(
            "https://data.educoder.net/api/accounts/login.json", json=config
        )

        userInfo = self.client.get(
            "https://data.educoder.net/api/users/get_user_info.json"
        ).json()
        log.debug(userInfo)
        self.userID = userInfo["login"]
        print(f"UserID: {self.userID}")

    def homework(self):
        course = self.select()
        courseURL = course["first_category_url"]
        courseID = courseURL.split("/")[2]

        homeworkCommons = self.client.get(
            "https://data.educoder.net/api/courses/f8nczpt6/homework_commons.json",
            params={"course_id": courseID, "type": 1},
        ).json()

        works = []
        for i in homeworkCommons["homeworks"]:
            if i["un_commit_work"]:
                payload = {
                    "coursesId": courseID,
                    "categoryId": i["homework_id"],
                    "id": courseID,
                }
                homework = self.client.get(
                    f"https://data.educoder.net/api/homework_commons/{i['homework_id']}/settings.json",
                    params=payload,
                ).json()
                works.append(homework)

        works.sort(key=lambda x: maya.when(x["end_time"]))
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column()
        table.add_column()
        table.add_column()
        for i in works:
            table.add_row(
                maya.when(i["end_time"]).datetime().strftime("%Y-%m-%d %H:%M"),
                i["homework_name"],
                maya.when(i["end_time"], timezone="Asia/Shanghai").slang_time("zh"),
            )
        print(table)

    def select(self):
        courses = self.client.get(
            f"https://data.educoder.net/api/users/{self.userID}/courses.json"
        ).json()

        for i, j in enumerate(courses["courses"]):
            print(f'{i}: {j["name"]} {j["first_category_url"]}')

        which = int(
            Prompt.ask(
                "Which course?",
                choices=[str(i) for i in range(len(courses["courses"]))],
                default=0,
            )
        )
        course = courses["courses"][which]
        print(f'Selected course: {course["name"]}')
        return course

    def attachment(self):
        course = self.select()
        courseURL = course["first_category_url"]
        courseID = courseURL.split("/")[2]

        files = self.client.get(
            "https://data.educoder.net/api/files.json", params={"course_id": courseID}
        ).json()

        with Progress() as progress:
            if not os.path.exists(f"Downloads/{course['name']}"):
                os.makedirs(f"Downloads/{course['name']}")

            task = progress.add_task(
                "Downloading files", total=len(files["data"]["files"])
            )

            for i, j in enumerate(files["data"]["files"]):
                progress.console.print(
                    f'Downloading [green]{j["title"]}[/green] {j["url"]}'
                )
                if os.path.exists(f'{course["name"]}/{j["title"]}'):
                    print(f'{j["title"]} already existed')
                    progress.update(task, advance=1)
                    continue
                file = self.client.get(f'https://data.educoder.net{j["url"]}').content
                progress.update(task, advance=0.5)
                with open(f'Downloads/{course["name"]}/{j["title"]}', "wb") as f:
                    f.write(file)
                    progress.update(task, advance=0.5)


if __name__ == "__main__":
    coder = EduCoder()
    coder.homework()
