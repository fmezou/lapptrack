"""Implementation of the MakeMKV product class

Classes
    Product : MakeMKV product class

Exception

Function

Constant

"""


import os
import datetime
import logging

from cots import core
from cots import pad
from cots import semver


class Product(core.BaseProduct):
    """MakeMKV product class.

    Public instance variables
        Same as `core.BaseProduct`.

    Public methods
        Same as `core.BaseProduct`.

    Subclass API variables (i.e. may be use by subclass)
        None

    Subclass API Methods (i.e. must be overwritten by subclass)
        None
    """
    def __init__(self, logger=logging.getLogger(__name__)):
        """Constructor

        Parameters
            :param logger: is a logger object

        Exception
            None
        """
        super().__init__(logger)

        # At this point, only name and catalog location are known.
        # All others attributes will be discovered during catalog parsing
        # (`check_update`) and update downloading (`fetch_update`)
        self.name = "MakeMKV"
        self._catalog_location = "http://www.makemkv.com/makemkv.xml"
        self._parser = pad.PadParser()

    def check_update(self):
        """Checks if a new version is available.

        The latest catalog of the product is downloaded and parsed.
        This catalog is a PAD File (see `pad` module).

        Parameters
            None

        Exceptions
            pad module exception raised by the `parse` method.
            exception raised by the `_temporary_retrieve` method.
        """
        msg = "Checks if a new version is available. Current version is '{0}'"
        self._logger.info(msg.format(self.version))

        local_filename, headers = \
            self._temporary_retrieve(self._catalog_location)
        msg = "Catalog downloaded: '{0}'".format(local_filename)
        self._logger.debug(msg)

        # Parse the catalog based on a PAD File
        # Reset the update property to have a up to date products catalog.
        # (i.e. obsolete information may be retrieved during the last checking)
        if self.update is not None:
            del self.update
            self.update = None
        self._parser.parse(local_filename)
        version = self._get_version()
        if version is not None:
            local_version = semver.SemVer(self.version)
            remote_version = semver.SemVer(self._get_version())
            if local_version < remote_version:
                prod = Product()
                prod.version = version
                prod.published = self._get_release_date()
                prod.location = self._get_location()
                self.update = prod
                msg = "A new version exist ({0}) published on {1}."
                msg = msg.format(self.update.version, self.update.published)
                self._logger.info(msg)
            else:
                msg = "No new version available."
                self._logger.info(msg)

        # clean up the temporary files
        os.unlink(local_filename)

    def fetch_update(self, path):
        """Downloads the latest version of the installer.

        Parameters
            :param path: is the path name where to store the installer package.

        Exceptions
            exception raised by the `_file_retrieve` method.
        """
        msg = "Downloads the latest version of the installer."
        self._logger.info(msg)

        # Update the update object
        prod = self.update
        if prod is not None:
            local_filename, headers = \
                self._file_retrieve(prod.location, path)

            prod.target = ""
            prod.release_note = self._get_release_note()
            prod.std_inst_args = ""
            prod.silent_inst_args = "/S"
            prod.product_code = ""
            prod._rename_installer(local_filename)
            self.load(prod.dump())  # update the current instance
            msg = "Update downloaded in '{}'".format(self.installer)
            self._logger.info(msg)
        else:
            msg = "No new version available."
            self._logger.info(msg)

    def _get_version(self):
        """Get the version from the PAD File.

        :return: a string specifying the version or None.
        """
        version = None
        path = "Program_Info/Program_Version"
        item = self._parser.find(path)
        if item is not None:
            version = item.text
            msg = "Program version :'{0}'"
            self._logger.info(msg.format(version))
        else:
            msg = "Unknown program version"
            self._logger.warning(msg)
        return version

    def _get_release_date(self):
        """Get the release date from the PAD File.

        :return: a string specifying the release date in ISO format or None.
        """
        release_date = None
        path = "Program_Info/Program_Release_Year"
        item = self._parser.find(path)
        if item is not None:
            year = int(item.text)
            path = "Program_Info/Program_Release_Month"
            item = self._parser.find(path)
            if item is not None:
                month = int(item.text)
                path = "Program_Info/Program_Release_Day"
                item = self._parser.find(path)
                if item is not None:
                    day = int(item.text)
                    dt = datetime.date(year, month, day)
                    release_date = dt.isoformat()
                    msg = "Release date :'{0}'"
                    self._logger.info(msg.format(release_date))
                else:
                    msg = "Unknown release day"
                    self._logger.warning(msg)
            else:
                msg = "Unknown release month"
                self._logger.warning(msg)
        else:
            msg = "Unknown release year"
            self._logger.warning(msg)

        return release_date

    def _get_release_note(self):
        """Get the release note URL from the PAD File.

        :return: a string specifying the URL or None.
        """
        release_note = "http://www.makemkv.com/download/"
        msg = "Release note :'{0}'"
        self._logger.info(msg.format(release_note))
        return release_note

    def _get_location(self):
        """Get the location from the PAD File.

        :return: a string specifying the version or None.
        """
        location = None
        path = "Web_Info/Download_URLs/Primary_Download_URL"
        item = self._parser.find(path)
        if item is not None:
            location = item.text
            msg = "Download url (for windows version) :'{0}'"
            self._logger.info(msg.format(location))
        else:
            msg = "Unknown Download url"
            self._logger.warning(msg)
        return location
