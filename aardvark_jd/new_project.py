#!/usr/bin/env python
# encoding: utf-8
"""
*Create a new project folder under Projects, from a template zip or blank*

Author
: David Young
"""

import glob
import os
import shutil
import sys
import zipfile

from aardvark_jd import db, emoji_picker, folders, paths

BLANK_CHOICE = "blank"


class new_project(object):
    """
    *create a new project folder, either from a `04_templates` zip or a blank scaffold*

    Projects are not Johnny-Decimal coded - they live directly under
    `P.ROJECTS/`.

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``templateName`` -- the template zip's basename (with or without `.zip`), or `"blank"`. If `None`, prompts interactively. Default `None`.
    - ``projectTitle`` -- the new project's title. If `None`, prompts interactively. Default `None`.
    - ``chosenEmoji`` -- an emoji supplied on the command-line, bypassing the suggester. Default `None`.
    - ``settings`` -- the aardvark settings dict. Default `None`.

    **Usage:**

    ```python
    from aardvark_jd.new_project import new_project
    title, folderPath, templateUsed = new_project(log=log, dbConn=dbConn).get()
    ```
    """

    def __init__(self, log, dbConn, templateName=None, projectTitle=None, chosenEmoji=None, settings=None):
        self.log = log
        self.dbConn = dbConn
        self.templateName = templateName
        self.projectTitle = projectTitle
        self.chosenEmoji = chosenEmoji
        self.settings = settings

    def get(self):
        """
        *resolve the template choice and title, then create the project*

        **Return:**

        - ``title`` -- the new project's title
        - ``folderPath`` -- the new project folder's absolute path
        - ``templateUsed`` -- `"blank"` or the template zip's basename
        """
        self.log.debug("starting the ``get`` method")

        templatesFolder = paths.resolve(self.dbConn, "projects.system.04_templates")
        templateZips = sorted(glob.glob(f"{templatesFolder}/*.zip"))

        templateChoice = self._resolve_template_choice(templateZips)
        title = self._resolve_title()

        pickedEmoji = emoji_picker.resolve_emoji(
            title, chosenEmoji=self.chosenEmoji, settings=self.settings, log=self.log
        )
        folderName = folders.project_folder_name(title, pickedEmoji)
        parentPath = paths.resolve(self.dbConn, "root.projects")
        folderPath = folders.make_folder(parentPath, folderName)

        if templateChoice == BLANK_CHOICE:
            self._build_blank_scaffold(folderPath)
            templateUsed = BLANK_CHOICE
        else:
            with zipfile.ZipFile(templateChoice) as zipHandle:
                zipHandle.extractall(folderPath)
            templateUsed = os.path.basename(templateChoice)

        db.insert_project(self.dbConn, title, "", pickedEmoji, folderName, folderPath, templateUsed)

        self.log.debug("completed the ``get`` method")
        return title, folderPath, templateUsed

    def _resolve_template_choice(self, templateZips):
        """
        *resolve which template to use, from the constructor arg or an interactive prompt*

        **Key Arguments:**

        - ``templateZips`` -- the available template zip paths

        **Return:**

        - ``choice`` -- `"blank"` or the chosen zip's path
        """
        if self.templateName is not None:
            if self.templateName == BLANK_CHOICE:
                return BLANK_CHOICE
            for zipPath in templateZips:
                basename = os.path.basename(zipPath)
                if self.templateName in (basename, basename[: -len(".zip")]):
                    return zipPath
            raise ValueError(f"no template named '{self.templateName}' found in '04_templates'")

        if not sys.stdin.isatty():
            self.log.warning("non-interactive session with no <templateName> given - defaulting to blank")
            return BLANK_CHOICE

        print("Available project templates:")
        print(f"  0) {BLANK_CHOICE} (README.md, input/, output/)")
        for index, zipPath in enumerate(templateZips, start=1):
            print(f"  {index}) {os.path.basename(zipPath)}")

        while True:
            choice = input("Select a template [0]: ").strip() or "0"
            if choice.isdigit() and 0 <= int(choice) <= len(templateZips):
                break
            print("Invalid choice, try again.")

        return BLANK_CHOICE if choice == "0" else templateZips[int(choice) - 1]

    def _resolve_title(self):
        """
        *resolve the project title, from the constructor arg or an interactive prompt*

        **Return:**

        - ``title`` -- the new project's title
        """
        if self.projectTitle:
            return self.projectTitle
        if not sys.stdin.isatty():
            raise ValueError("a <projectTitle> is required in non-interactive sessions")
        while True:
            title = input("Project title: ").strip()
            if title:
                return title
            print("A project title is required.")

    def _build_blank_scaffold(self, folderPath):
        """
        *populate a project folder with the bundled blank scaffold (README.md, input/, output/)*

        **Key Arguments:**

        - ``folderPath`` -- the new project folder's absolute path
        """
        sourceDirectory = os.path.dirname(__file__) + "/resources/templates_src/blank_starter"
        for entry in os.listdir(sourceDirectory):
            sourcePath = os.path.join(sourceDirectory, entry)
            destinationPath = os.path.join(folderPath, entry)
            if os.path.isdir(sourcePath):
                shutil.copytree(sourcePath, destinationPath)
            else:
                shutil.copy2(sourcePath, destinationPath)
