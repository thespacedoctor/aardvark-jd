#!/usr/bin/env python
# encoding: utf-8
"""
*Initialise a new aardvark PARA + Johnny Decimal root*

Author
: David Young
"""

import os
import zipfile

from aardvark_jd import db, folders, paths, settings_writer

_BLANK_TEMPLATE_NAME = "blank_starter.zip"


class initialiser(object):
    """
    *build a new aardvark root folder tree, its SQLite index, and persist the active system in the user settings*

    **Key Arguments:**

    - ``log`` -- logger
    - ``systemName`` -- the name of the new system, e.g. `"My Life"`
    - ``parentPath`` -- the path in which the system's root folder should be created
    - ``pathToSettingsFile`` -- path to the aardvark user settings YAML file

    **Usage:**

    ```python
    from aardvark_jd.initialiser import initialiser
    rootPath = initialiser(
        log=log,
        systemName="My Life",
        parentPath="/Users/dave",
        pathToSettingsFile="~/.config/aardvark/aardvark.yaml"
    ).get()
    ```
    """

    def __init__(self, log, systemName, parentPath, pathToSettingsFile):
        self.log = log
        self.systemName = systemName
        self.parentPath = parentPath.rstrip("/")
        self.pathToSettingsFile = os.path.expanduser(pathToSettingsFile)

    def get(self):
        """
        *build the root folder tree and index, and return the root path*

        **Return:**

        - ``rootPath`` -- the new (or already-existing) system root path
        """
        self.log.debug("starting the ``get`` method")

        rootPath = f"{self.parentPath}/{self.systemName}"
        os.makedirs(rootPath, exist_ok=True)

        createdPaths = self._create_skeleton_folders(rootPath)

        indexFolderPath = createdPaths["root.index"][1]
        dbConn = db.get_connection(paths.get_db_path_in_folder(indexFolderPath))
        db.initialise_schema(dbConn)
        self._record_system_folders(dbConn, createdPaths)
        self._seed_blank_template(createdPaths["projects.system.04_templates"][1])
        dbConn.close()

        self._update_settings(rootPath)

        self.log.debug("completed the ``get`` method")
        return rootPath

    def _create_skeleton_folders(self, rootPath):
        """
        *create every static folder in `paths.SYSTEM_SKELETON`, using its declared emoji*

        The skeleton is a fixed, known list, so each folder's emoji is
        declared alongside it in `paths.SYSTEM_SKELETON` rather than
        guessed from the title.

        **Key Arguments:**

        - ``rootPath`` -- the system root path

        **Return:**

        - ``createdPaths`` -- a dict mapping folder key -> (folderName, folderPath)
        """
        createdPaths = {}
        for folderKey, parentKey, baseName, _title, _description, folderEmoji in paths.SYSTEM_SKELETON:
            parentPath = rootPath if parentKey is None else createdPaths[parentKey][1]
            folderName = folders.system_folder_name(baseName, folderEmoji)
            folderPath = folders.make_folder(parentPath, folderName)
            createdPaths[folderKey] = (folderName, folderPath)
        return createdPaths

    def _record_system_folders(self, dbConn, createdPaths):
        """
        *persist every created folder's exact name/path to the `system_folders` table*

        **Key Arguments:**

        - ``dbConn`` -- an open SQLite connection
        - ``createdPaths`` -- a dict mapping folder key -> (folderName, folderPath)
        """
        for folderKey, (folderName, folderPath) in createdPaths.items():
            db.insert_system_folder(dbConn, folderKey, folderName, folderPath)

    def _seed_blank_template(self, templatesFolderPath):
        """
        *generate the bundled blank project template zip, if it does not already exist*

        **Key Arguments:**

        - ``templatesFolderPath`` -- the projects `04_templates` folder path
        """
        pathToZip = f"{templatesFolderPath}/{_BLANK_TEMPLATE_NAME}"
        if os.path.exists(pathToZip):
            return

        sourceDirectory = os.path.dirname(__file__) + "/resources/templates_src/blank_starter"
        with zipfile.ZipFile(pathToZip, "w", zipfile.ZIP_DEFLATED) as zipHandle:
            for dirPath, _dirNames, fileNames in os.walk(sourceDirectory):
                for fileName in fileNames:
                    filePath = os.path.join(dirPath, fileName)
                    arcName = os.path.relpath(filePath, sourceDirectory)
                    zipHandle.write(filePath, arcName)

    def _update_settings(self, rootPath):
        """
        *persist the active system's name/root path to the user settings YAML file*

        **Key Arguments:**

        - ``rootPath`` -- the new (or already-existing) system root path
        """
        settings = settings_writer.read_settings(self.pathToSettingsFile)
        settings.setdefault("system", {})
        settings["system"]["name"] = self.systemName
        settings["system"]["root_path"] = rootPath
        settings_writer.write_settings(self.pathToSettingsFile, settings)
