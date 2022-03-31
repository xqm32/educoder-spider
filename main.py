import json
import logging
import os

import requests
from rich import print
from rich.logging import RichHandler
from rich.progress import Progress
from rich.prompt import Prompt
from rich.traceback import install

install(max_frames=1)

FORMAT = '%(message)s'
logging.basicConfig(
    level='INFO',
    format=FORMAT,
    datefmt='[%X]',
    handlers=[RichHandler(rich_tracebacks=True)]
)

log = logging.getLogger('rich')


def main():
    if os.path.exists('config.json'):
        with open('config.json') as f:
            config = json.load(f)
    else:
        username = Prompt.ask('Username')
        password = Prompt.ask('Password', password=True)
        config = {'login': username, 'password': password}

    print(f'Read config of {config["login"]}')

    session = requests.session()
    session.post(
        'https://data.educoder.net/api/accounts/login.json',
        json=config
    )

    userInfo = session.get(
        'https://data.educoder.net/api/users/get_user_info.json'
    ).json()
    log.debug(userInfo)
    userID = userInfo['login']
    print(f'UserID: {userID}')

    courses = session.get(
        'https://data.educoder.net/api/users/p8lb45t3h/courses.json'
    ).json()

    for i, j in enumerate(courses['courses']):
        print(f'{i}: {j["name"]} {j["first_category_url"]}')

    which = int(Prompt.ask(
        'Which course?',
        choices=[str(i) for i in range(len(courses['courses']))],
        default=0
    ))
    course = courses['courses'][which]
    print(f'Selected course: {course["name"]}')
    courseURL = course['first_category_url']
    courseID = courseURL.split('/')[2]

    files = session.get(
        'https://data.educoder.net/api/files.json',
        params={'course_id': courseID}
    ).json()

    with Progress() as progress:
        if not os.path.exists(course['name']):
            os.mkdir(course['name'])

        task = progress.add_task(
            'Downloading files',
            total=len(files['data']['files'])
        )

        for i, j in enumerate(files['data']['files']):
            progress.console.print(
                f'Downloading [green]{j["title"]}[/green] {j["url"]}'
            )
            file = session.get(f'https://data.educoder.net{j["url"]}').content
            progress.update(task, advance=0.5)
            with open(f'{course["name"]}/{j["title"]}', 'wb') as f:
                f.write(file)
                progress.update(task, advance=0.5)


if __name__ == '__main__':
    main()
