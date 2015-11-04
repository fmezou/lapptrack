"""Check and download applications' updates if any.

Usage
appdownload.py [-h] [-c | -d | -t] [--version]

optional arguments:
  -h, --help            show this help message and exit
  -c, --checkonly       check and report if applications' updates are
                        available without download it
  -d, --download        download applications' updates based on the last build
                        catalog (useful to recover a crashed application
                        storage)
  -m, --make            make applist files based on the last build
                        catalog (useful to make applist files after a
                        configuration modification)
  -t, --testconf        check an appdownload.ini configuration file for
                        internal correctness
  --configfile CONFIGFILE
                        The file specified contains the configuration details.
                        The information in this file includes application
                        catalog. See appdownload.ini for more information.
                        The default configuration file name is 'appdownload.ini'
                        located in the current working directory.
  --version             show program's version number and exit

Exit code
  0: no error
  1: an error occurred (error messages are print on stderr stream console
     and write in a log file.
  2: invalid argument. An argument of the command line isn't valid (see Usage).

Environment variables
The following environment variables affect the execution of this script:
#TODO:
"""

import io
import os.path
import datetime
import argparse
import configparser
import importlib
import logging
import logging.config

from cots import core


__author__ = "Frederic MEZOU"
__version__ = "0.3.0-dev"
__license__ = "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007"


# Sections and values names used in the configuration file (see appdownload.ini)
_APPS_LIST_SECTNAME = "applications"
_APP_INSTALL_KEYNAME = "install"
_APP_MODULE_KEYNAME = "module"
_APP_PATH_KEYNAME = "path"
_APP_SET_KEYNAME = "set"

_CORE_SECTNAME = "core"
_STORE_KEYNAME = "store"

_SETS_LIST_SECTNAME = "sets"

# Sections and values names used in the catalog file (see catalog.ini)
_CATALOG_FILENAME = "catalog.ini"
_PROD_NAME_KEYNAME = "name"
_PROD_VERSION_KEYNAME = "version"
_PROD_PUBDATE_KEYNAME = "published"
_PROD_TARGET_KEYNAME = "target"
_PROD_TARGET_X86 = "x86"
_PROD_TARGET_X64 = "x64"
_PROD_TARGET_UNIFIED = "unified"
_PROD_REL_NOTE_URL_KEYNAME = "release_note"
_PROD_INSTALLER_KEYNAME = "installer"
_PROD_STD_INSTALL_ARGS_KEYNAME = "std_inst_args"
_PROD_SILENT_INSTALL_ARGS_KEYNAME = "silent_inst_args"
_PROD_UPDATE_AVAIL_KEYNAME = "update_available"
_PROD_UPDATE_VERSION_KEYNAME = "update_version"
_PROD_UPDATE_PUBDATE_KEYNAME = "update_published"

# APPLIST files
_APPLIST_SEP = ";"
_APPLIST_PREFIX = "applist-"
_APPLIST_EXT = ".txt"


class Error(Exception):
    """Base class for AppDownload exceptions."""

    def __init__(self, message=""):
        self.message = message

    def __str__(self):
        return self.message


class MissingMandatorySectionError(Error):
    """Raised when a mandatory section is missing."""

    def __init__(self, section_name):
        """constructor.

        Parameters
            section_name: Name of the missing section.
        """
        msg = "Section '{0}' is missing."
        Error.__init__(self, msg.format(section_name))
        self.section_name = section_name


class MissingAppSectionError(Error):
    """ Raised when an application description section is missing."""

    def __init__(self, section_name):
        """constructor.

        Parameters
            section_name: Name of the missing section.
        """
        msg = "Application description section '{0}' is missing."
        Error.__init__(self, msg.format(section_name))
        self.section_name = section_name


class MissingKeyError(Error):
    """ Raised when a key section is missing in a section."""

    def __init__(self, section_name, keyname):
        """constructor.

        Parameters
            section_name: Name of the section containing the missing key.
            keyname: name of missing key.
        """
        msg = "Key '{1}' is missing in '{0}' application description."
        Error.__init__(self, msg.format(section_name, keyname))
        self.section_name = section_name
        self.keyname = keyname


class NotDeclaredSetError(Error):
    """ Raised when a set not declared in the sets section."""

    def __init__(self, app_name, set_name):
        """constructor.

        Parameters
            app_name: name of the application (i.e containing the missing key.
            set_name: name of missing set.
        """
        msg = "Set '{1}' is not declared in Sets section for application " \
              "named '{0}'."
        Error.__init__(self, msg.format(set_name, app_name))
        self.app_name = app_name
        self.set_name = set_name


class AppDownload:
    """Application class.

    Public instance variables
        None

    Public methods
        None

    Subclass API variables (i.e. may be use by subclass)
        None

    Subclass API Methods (i.e. must be overwritten by subclass)
        None
    """

    def __init__(self, config_file):
        """constructor.

        Parameters
            config_file: Name of the configuration file. The name may be a
            partial one or a full path one.
        """
        # check parameters type
        if not isinstance(config_file, io.TextIOBase):
            msg = "config_file argument must be a class 'io.TextIOBase'. not {0}"
            msg = msg.format(config_file.__class__)
            raise TypeError(msg)

        # initialise the configuration based on ConfigParser module.
        self._config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation())
        self._checked_config = False
        self._config_file = config_file

        # initialise the application catalog based on ConfigParser module.
        self._catalog_filename = ""
        self._catalog = configparser.ConfigParser()
        self._app_set_file = {}

        # initialise the logging based on logging module.
        self.logger = logging.getLogger(__name__)

    def run(self):
        """run the AppDownload application.

        Parameters
            None
        """
        self._load_config()
        self.logger.info("Starting Appdowload (%s)", __version__)
        self._read_catalog()
        self._check_update()
        self._fetch_update()
        self._write_catalog()
        self._write_applist()
        self.logger.info("Appdowload (%s) completed.", __version__)

    def check(self):
        """check and report if applications' updates are available without
         download it.

        Parameters
            None
        """
        self._load_config()
        self.logger.info("Starting Appdowload (%s), check and report if "
                         "applications' updates are available.", __version__)
        self._read_catalog()
        self._check_update()
        self._write_catalog()
        self.logger.info("Appdowload (%s) completed.", __version__)

    def download(self):
        """download applications' updates based on the last build catalog.

        Parameters
            None
        """
        self._load_config()
        self.logger.info("Starting Appdowload (%s), download applications' "
                         "updates based on the last build catalog.",
                         __version__)
        self._read_catalog()
        self._fetch_update()
        self._write_catalog()
        self.logger.info("Appdowload (%s) completed.", __version__)

    def make(self):
        """make applist files based on the last build catalog

        Parameters
            None
        """
        self._load_config()
        self.logger.info("Starting Appdowload (%s), make applist files based "
                         "on the last build catalog.", __version__)
        self._read_catalog()
        self._write_applist()
        self.logger.info("Appdowload (%s) completed.", __version__)

    def test_config(self):
        """check the configuration file for internal correctness.

        Parameters
            None
        """
        # The logging configuration may be not valid, events are only print on
        # the console with print(). Furthermore, the use case of this method is
        # typically in interactive mode.
        print("Starting Appdowload ({0}), check the configuration file for "
              "internal correctness.".format(__version__))
        print("Configuration details are loaded from '{0}'."
              .format(self._config_file.name))
        self._load_config()
        if self._checked_config:
            print("Configuration details are validated.")
        print("Appdowload ({0}) completed.".format(__version__))

    def _check_update(self):
        """check and report if applications' updates are available without
         download it.


        Parameters
            None
        """
        assert self._checked_config is True

        self.logger.info("Checking and report if applications' updates are "
                         "available.")
        for app_id in self._config[_APPS_LIST_SECTNAME]:
            if self._config[_APPS_LIST_SECTNAME].getboolean(app_id):
                self.logger.debug("Load and set the '{0}' module.".format(app_id))
                mod_name = self._config[app_id][_APP_MODULE_KEYNAME]
                app_mod = importlib.import_module(mod_name)
                app = app_mod.Product()
                self._load_product(app_id, app)

                self.logger.debug("Check if an update is available")
                app.check_update()
                if app.update_available:
                    msg = "A new version of '{0}' exist ({1}) published " \
                          "on {2}.".format(app_id, app.update_version,
                                           app.update_published)
                    self.logger.info(msg)

                self._dump_product(app_id, app)
                del app
                del app_mod
                self.logger.debug("'{0}' checked.".format(app_id))
            else:
                self.logger.info("'{0}' ignored.".format(app_id))

    def _fetch_update(self):
        """download applications' updates based on the last build catalog.

        Parameters
            None
        """
        assert self._checked_config is True

        self.logger.info("Download applications' updates based on the last "
                         "build catalog.")
        for app_id in self._config[_APPS_LIST_SECTNAME]:
            if self._config[_APPS_LIST_SECTNAME].getboolean(app_id):
                self.logger.debug("Load and set the '{0}' module.".format(app_id))
                mod_name = self._config[app_id][_APP_MODULE_KEYNAME]
                app_mod = importlib.import_module(mod_name)
                app = app_mod.Product()
                self._load_product(app_id, app)

                self.logger.debug("Fetch the update.")
                if _APP_PATH_KEYNAME not in self._config[app_id]:
                    path = os.path.join(
                        self._config[_CORE_SECTNAME][_STORE_KEYNAME],
                        app_id
                    )
                else:
                    path = self._config[app_id][_APP_PATH_KEYNAME]
                app.fetch_update(path)
                msg = "The new version of '{0}' fetched. saved as '{1}'."\
                      .format(app_id, app.installer)
                self.logger.info(msg)

                self._dump_product(app_id, app)
                del app
                del app_mod
            else:
                self.logger.info("'{0}' ignored.".format(app_id))

    def _load_config(self):
        """load the configuration details from the configuration file.

        Parameters
            None
        """
        # Load the configuration, and set the logging configuration from it.
        # I'am still using the fileConfig() method instead of dictConfig() to
        # keep the configuration in a ini file, which is easy to write and to
        # read for a human.
        self._config.read_file(self._config_file)
        logging.config.fileConfig(self._config, disable_existing_loggers=True)

        # Check the core section
        if _CORE_SECTNAME in self._config.sections():
            section = self._config[_CORE_SECTNAME]
            # 'store' key is mandatory
            if _STORE_KEYNAME in section:
                # Set the catalog filename (absolute path).
                # TODO : treat the exception for os.makedirs
                os.makedirs(self._config[_CORE_SECTNAME][_STORE_KEYNAME], exist_ok=True)
                self._catalog_filename = os.path.join(
                    self._config[_CORE_SECTNAME][_STORE_KEYNAME],
                    _CATALOG_FILENAME
                )
                self._catalog_filename = os.path.abspath(self._catalog_filename)
            else:
                raise MissingKeyError(_STORE_KEYNAME, _CORE_SECTNAME)
        else:
            raise MissingMandatorySectionError(_CORE_SECTNAME)

        # Check the sets section
        if _SETS_LIST_SECTNAME in self._config.sections():
            sets = self._config[_SETS_LIST_SECTNAME]
        else:
            raise MissingMandatorySectionError(_SETS_LIST_SECTNAME)

        # Check the applications section
        if _APPS_LIST_SECTNAME in self._config.sections():
            for app_name in self._config[_APPS_LIST_SECTNAME]:
                if self._config[_APPS_LIST_SECTNAME].getboolean(app_name):
                    if app_name in self._config.sections():
                        app_desc = self._config[app_name]
                        # 'module' key is mandatory
                        if _APP_MODULE_KEYNAME in app_desc:
                            pass
                        else:
                            raise MissingKeyError(app_name, _APP_MODULE_KEYNAME)
                        # 'set' key is mandatory and must be declared in the sets section
                        if _APP_SET_KEYNAME in app_desc:
                            if app_desc[_APP_SET_KEYNAME] in sets:
                                pass
                            else:
                                raise NotDeclaredSetError(app_name, app_desc[_APP_SET_KEYNAME])
                        else:
                            raise MissingKeyError(app_name, _APP_SET_KEYNAME)
                    else:
                        raise MissingAppSectionError(app_name)
        else:
            raise MissingMandatorySectionError(_APPS_LIST_SECTNAME)
        # Checked
        self._checked_config = True
        self._config_file.close()
        self._config_file = None

    def _read_catalog(self):
        """load the product's catalog.

        Parameters
            None
        """
        msg = "Load the products' catalog ({0}).".format(self._catalog_filename)
        self.logger.info(msg)
        try:
            with open(self._catalog_filename, "r+t") as file:
                self._catalog.read_file(file)
        except FileNotFoundError:
            # the catalog may be not exist
            self.logger.warning("The product's catalog don't exist. A new one "
                                "will be created.")
        else:
            msg = "Products' catalog loaded, " \
                  "{0} products found.".format(len(self._catalog))
            self.logger.info(msg)

    def _write_catalog(self):
        """write the catalog product file.

        Parameters
            None
        """
        msg = "Write the products' catalog ({0}).".format(self._catalog_filename)
        self.logger.info(msg)

        header = \
            "# ------------------------------------------------------------------------------\n"\
            "# This file is automatically generated on {0},\n"\
            "# and must not be manually modified.\n"\
            "# It contains the applications database and specifies for each application the\n"\
            "# following properties. Appdownload script uses this database to build the\n"\
            "# applist files used by appdeploy script.\n"\
            "# ------------------------------------------------------------------------------\n"
        with open(self._catalog_filename, "w+t") as file:
            # write the warning header with a naive time representation.
            dt = (datetime.datetime.now()).replace(microsecond=0)
            file.write(header.format(dt.isoformat()))
            self._catalog.write(file)
        msg = "Products' catalog saved, " \
              "{0} products written.".format(len(self._catalog))
        self.logger.info(msg)

    def _load_product(self, section_name, product):
        """Load a product class from the catalog.

        Parameters
            section_name: is the name of the product used as a section name is
              the application catalog.
            product: is the Product class to load

        If the section don't exist, the method do nothing and leave the default
        value of class properties.

        """
        # TODO : make a choice between product and application, and use alway the same term
        # check parameters type
        if not isinstance(product, core.BaseProduct):
            msg = "product argument must be a class 'core.BaseProduct'. not {0}"
            msg = msg.format(product.__class__)
            raise TypeError(msg)
        if not isinstance(section_name, str):
            msg = "section_name argument must be a class 'str'. not {0}"
            msg = msg.format(section_name.__class__)
            raise TypeError(msg)

        msg = "Load the product '{0}' from the catalog.".format(section_name)
        self.logger.info(msg)

        if section_name in self._catalog.sections():
            app_props = self._catalog[section_name]
            product.id = section_name
            if _PROD_NAME_KEYNAME in app_props:
                product.name = app_props[_PROD_NAME_KEYNAME]
            if _PROD_VERSION_KEYNAME in app_props:
                product.version = app_props[_PROD_VERSION_KEYNAME]
            if _PROD_PUBDATE_KEYNAME in app_props:
                product.published = app_props[_PROD_PUBDATE_KEYNAME]
            if _PROD_TARGET_KEYNAME in app_props:
                product.target = app_props[_PROD_TARGET_KEYNAME]
            if _PROD_REL_NOTE_URL_KEYNAME in app_props:
                product.release_note = app_props[_PROD_REL_NOTE_URL_KEYNAME]
            if _PROD_INSTALLER_KEYNAME in app_props:
                product.installer = app_props[_PROD_INSTALLER_KEYNAME]
            if _PROD_STD_INSTALL_ARGS_KEYNAME in app_props:
                product.std_inst_args = app_props[_PROD_STD_INSTALL_ARGS_KEYNAME]
            if _PROD_SILENT_INSTALL_ARGS_KEYNAME in app_props:
                product.silent_inst_arg = app_props[_PROD_SILENT_INSTALL_ARGS_KEYNAME]
            if _PROD_UPDATE_AVAIL_KEYNAME in app_props:
                product.update_available = app_props.getboolean(_PROD_UPDATE_AVAIL_KEYNAME)
            if _PROD_UPDATE_VERSION_KEYNAME in app_props:
                product.update_version = app_props[_PROD_UPDATE_VERSION_KEYNAME]
            if _PROD_UPDATE_PUBDATE_KEYNAME in app_props:
                product.update_published = app_props[_PROD_UPDATE_PUBDATE_KEYNAME]

            msg = "Product '{0}' loaded.\n" + \
                  "Name: {1}\n" + \
                  "Version: {2}\n" + \
                  "Published on: {3}\n" + \
                  "Target: {4}\n" + \
                  "Release note: {5}\n" + \
                  "Installer: {6}\n" + \
                  "Standard arguments: {7}\n" + \
                  "Silent arguments: {8}\n" + \
                  "Update available: {9}\n" + \
                  "Update version: {10}\n" + \
                  "Update published on: {11}"
            msg = msg.format(product.id,
                             product.name,
                             product.version,
                             product.published,
                             product.target,
                             product.release_note,
                             product.installer,
                             product.std_inst_args,
                             product.silent_inst_arg,
                             product.update_available,
                             product.update_version,
                             product.update_published)
            self.logger.debug(msg)
        else:
            msg = "The product '{0}' don't exist. " \
                  "A new one will be created.".format(section_name)
            self.logger.warning(msg)

    def _dump_product(self, section_name, product):
        """Dump a product class.

        Parameters
            section_name: is the name of the product used as a section name is
              the application catalog.
            product: is the Product class to dump
        """
        # check parameters type
        if not isinstance(product, core.BaseProduct):
            msg = "product argument must be a class 'core.BaseProduct'. not {0}"
            msg = msg.format(product.__class__)
            raise TypeError(msg)
        if not isinstance(section_name, str):
            msg = "section_name argument must be a class 'str'. not {0}"
            msg = msg.format(section_name.__class__)
            raise TypeError(msg)

        msg = "Save the product '{0}' to the catalog.".format(section_name)
        self.logger.info(msg)

        if section_name not in self._catalog.sections():
            self._catalog.add_section(section_name)
        else:
            # reset the section to delete any obsolete keys
            self._catalog.remove_section(section_name)
            self._catalog.add_section(section_name)
        app_props = self._catalog[section_name]
        app_props[_PROD_NAME_KEYNAME] = product.name
        app_props[_PROD_VERSION_KEYNAME] = product.version
        app_props[_PROD_PUBDATE_KEYNAME] = product.published
        app_props[_PROD_TARGET_KEYNAME] = product.target
        app_props[_PROD_REL_NOTE_URL_KEYNAME] = product.release_note
        app_props[_PROD_INSTALLER_KEYNAME] = product.installer
        app_props[_PROD_STD_INSTALL_ARGS_KEYNAME] = product.std_inst_args
        app_props[_PROD_SILENT_INSTALL_ARGS_KEYNAME] = product.silent_inst_arg
        if product.update_available:
            app_props[_PROD_UPDATE_AVAIL_KEYNAME] = "yes"
        else:
            app_props[_PROD_UPDATE_AVAIL_KEYNAME] = "no"
        app_props[_PROD_UPDATE_VERSION_KEYNAME] = product.update_version
        app_props[_PROD_UPDATE_PUBDATE_KEYNAME] = product.update_published

        msg = "Product '{0}' saved.\n" + \
              "Name: {1}\n" + \
              "Version: {2}\n" + \
              "Published on: {3}\n" + \
              "Target: {4}\n" + \
              "Release note: {5}\n" + \
              "Installer: {6}\n" + \
              "Standard arguments: {7}\n" + \
              "Silent arguments: {8}\n" + \
              "Update available: {9}\n" + \
              "Update version: {10}\n" + \
              "Update published on: {11}"
        msg = msg.format(section_name,
                         product.name,
                         product.version,
                         product.published,
                         product.target,
                         product.release_note,
                         product.installer,
                         product.std_inst_args,
                         product.silent_inst_arg,
                         product.update_available,
                         product.update_version,
                         product.update_published)
        self.logger.debug(msg)

    def _write_applist(self):
        """Write the applist files from the catalog.

        Parameters
            None
        """
        self.logger.info("Write the applist files from the catalog.")

        header = \
            "# ------------------------------------------------------------------------------\n"\
            "# This applist file generated on {0} for '{1}'.\n"\
            "# This file is automatically generated, and must not be manually modified.\n"\
            "# Please modify the configuration file instead (appdowload.ini by default).\n"\
            "# ------------------------------------------------------------------------------\n"

        for app_id in self._config[_APPS_LIST_SECTNAME]:
            if self._config[_APPS_LIST_SECTNAME].getboolean(app_id):
                # build the catalog line
                app_desc = self._catalog[app_id]
                app_line = \
                    app_desc[_PROD_TARGET_KEYNAME] + _APPLIST_SEP + \
                    app_desc[_PROD_NAME_KEYNAME] + _APPLIST_SEP + \
                    app_desc[_PROD_VERSION_KEYNAME] + _APPLIST_SEP + \
                    app_desc[_PROD_INSTALLER_KEYNAME] + _APPLIST_SEP + \
                    app_desc[_PROD_SILENT_INSTALL_ARGS_KEYNAME]

                store_path = self._config[_CORE_SECTNAME][_STORE_KEYNAME]
                app_set_name = self._config[app_id][_APP_SET_KEYNAME]
                comps = self._config[_SETS_LIST_SECTNAME][app_set_name]
                comp_set = comps.split(",")
                for comp_name in comp_set:
                    comp_name = comp_name.strip()
                    filename = _APPLIST_PREFIX + comp_name + _APPLIST_EXT
                    filename = os.path.join(store_path, filename)
                    if comp_name not in self._app_set_file:
                        file = open(filename, "w+t")
                        self._app_set_file[comp_name] = file
                        self.logger.info("'{0}' applist file created -> '{1}'.".format(comp_name, filename))
                        dt = (datetime.datetime.now()).replace(microsecond=0)
                        file.write(header.format(dt.isoformat(), comp_name))
                    else:
                        file = self._app_set_file[comp_name]
                    file.write(app_line + "\n")
            else:
                self.logger.info("'{0}' ignored.".format(app_id))

        # Terminate by closing the files
        for comp_name, file in self._app_set_file.items():
            file.close()


if __name__ == "__main__":
    # Entry point
    # Build the command line parser
    parser = argparse.ArgumentParser(
        description="Check and download applications\' updates if any.")
    general = parser.add_mutually_exclusive_group()
    general.add_argument("-c", "--checkonly", action="store_true",
                         help="check and report if applications' updates are "
                              "available without download it")
    general.add_argument("-d", "--download", action="store_true",
                         help="download applications' updates based on the "
                              "last build catalog (useful to recover a crashed "
                              "application storage)")
    general.add_argument("-m", "--make", action="store_true",
                         help="make applist files based on the last build "
                              "catalog (useful to make applist files after a "
                              "configuration modification)")
    general.add_argument("-t", "--testconf", action="store_true",
                         help="check an appdownload.ini configuration file for "
                              "internal correctness")
    parser.add_argument("--configfile", default="appdownload.ini",
                        type=argparse.FileType(mode='r'),
                        help="The file specified contains the configuration "
                             "details. The information in this file includes "
                             "application catalog. See appdownload.ini for "
                             "more information. The default configuration file "
                             "name is 'appdownload.ini' located in the current "
                             "working directory.")
    parser.add_argument("--version", action="version",
                        version="%(prog)s version " + __version__)

    # Parse and run.
    args = parser.parse_args()
    main_task = AppDownload(args.configfile)
    if args.checkonly:
        main_task.check()
    elif args.download:
        main_task.download()
    elif args.make:
        main_task.make()
    elif args.testconf:
        main_task.test_config()
    else:
        main_task.run()
