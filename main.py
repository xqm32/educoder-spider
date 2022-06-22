from itertools import count
import json
import logging
import os

import httpx
import maya
from rich import print
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

        works = []

        for i in count(1):
            homeworkCommons = self.client.get(
                "https://data.educoder.net/api/courses/f8nczpt6/homework_commons.json",
                params={"course_id": courseID, "type": 1, "page": i},
            ).json()

            if not homeworkCommons["homeworks"]:
                break

            print(f"正在加载第 {i} 页")

            for j in homeworkCommons["homeworks"]:
                if j["un_commit_work"]:
                    payload = {
                        "coursesId": courseID,
                        "categoryId": j["homework_id"],
                        "id": courseID,
                    }
                    homework = self.client.get(
                        f"https://data.educoder.net/api/homework_commons/{j['homework_id']}/settings.json",
                        params=payload,
                    ).json()
                    works.append(homework)

            print(f"第 {i} 页加载完成，已获取 {len(works)} 个任务")

        works.sort(key=lambda x: maya.when(x["end_time"]))
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column()
        table.add_column()
        table.add_column()
        for i in works:
            table.add_row(
                maya.when(i["end_time"], timezone="Asia/Shanghai")
                .datetime(to_timezone="Asia/Shanghai")
                .strftime("%Y-%m-%d %H:%M"),
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
                "选择课程: ",
                choices=[str(i) for i in range(len(courses["courses"]))],
                default=0,
            )
        )
        course = courses["courses"][which]
        print(f'选择了: {course["name"]}')
        return course

    def attachment(self):
        course = self.select()
        courseURL = course["first_category_url"]
        courseID = courseURL.split("/")[2]

        files = self.client.get(
            "https://data.educoder.net/api/files.json",
            params={"course_id": courseID, "clazz": "1"},
        ).json()

        print(f"共有 {len(files['data']['files'])} 个文件")

        with Progress() as progress:
            if not os.path.exists(f"Downloads/{course['name']}"):
                os.makedirs(f"Downloads/{course['name']}")

            task = progress.add_task(
                "Downloading files", total=len(files["data"]["files"])
            )

            for i, j in enumerate(files["data"]["files"]):
                progress.console.print(
                    f'Downloading [green]{j["title"]}[/green] {j["url"]} to Downloads/{course["name"]}/{j["title"]}'
                )
                if os.path.exists(f'Downloads/{course["name"]}/{j["title"]}'):
                    progress.console.print(f'{j["title"]} already existed')
                    progress.update(task, advance=1)
                    continue
                file = self.client.get(f'https://data.educoder.net{j["url"]}').content
                progress.update(task, advance=0.5)
                with open(f'Downloads/{course["name"]}/{j["title"]}', "wb") as f:
                    f.write(file)
                    progress.update(task, advance=0.5)


if __name__ == "__main__":
    coder = EduCoder()
    coder.attachment()
