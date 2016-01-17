"""Implementation of a dummy product class.

Classes
    Product : dummy product class

Exception

Function

Constant

"""


import datetime
import logging
import semver

from cots import core


# To make the module as versatile as possible, an nullHandler is added.
# see 'Configuring Logging for a Library'
# docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class Product(core.BaseProduct):
    """Dummy product class.

    Public instance variables
        Same as `core.BaseProduct`.

    Public methods
        Same as `core.BaseProduct`.

    Subclass API variables (i.e. may be use by subclass)
        None

    Subclass API Methods (i.e. must be overwritten by subclass)
        None
    """
    def __init__(self):
        """Constructor

        Parameters
            None

        Exception
            None
        """
        super().__init__()

        # At this point, only name and catalog url are known.
        # All others attributes will be discovered during catalog parsing
        # (`get_origin`) and update downloading (`fetch`)
        self.name = "Dummy Product"
        self._catalog_url = "http://www.example.com/index.html"

    def is_update(self, product):
        """ Return if this instance is an update of product

        This method compare the version of the two product, and return the
        comparison result. The version numbers used by the editor are compliant
        with the semantic versioning specification 2.0.0 (see `semver`module)

        Parameters
            :param product: is the reference product (i.e. the deployed product)

        Exceptions
            `semver` module exception raised by the rich comparison method of
            SemVer class.

        Returns
            :return: true if this instance is an update of the product specified
            by the `product` parameter.
        """
        # check parameters type
        if not isinstance(product, Product):
            msg = "product argument must be a class 'makemv.product'. not {0}"
            msg = msg.format(product.__class__)
            raise TypeError(msg)

        # comparison based on version number.
        result = False
        if semver.SemVer(self.version) < semver.SemVer(product.version):
            result = True
            msg = "A new version exist ({})."
            _logger.debug(msg.format(product.version))
        else:
            msg = "No new version available."
            _logger.debug(msg)
        return result

    def _parse_catalog(self, filename):
        """ Parse the catalog.

        This method parses the downloaded product catalog to prepare
        `_get_...` call.
        This catalog is a PAD File (see `pad` module).

        Parameters
            :param filename: is a string specifying the local name of the
            downloaded product catalog.
         """
        _logger.debug(filename)

    def _get_name(self):
        """
        Extract the name of the product (used in report mail and log file).
        """
        self.name = "Dummy Product"

    def _get_display_name(self):
        """Extract the name of the product as it appears in the 'Programs and
        Features' control panel.

        This name is built from the name and the version attribute, thus this
        method must be called after `_get_name` and `_get_version`.
        """
        name = "{} ({})"
        self.display_name = name.format(self.name, self.version)

    def _get_version(self):
        """Extract the current version of the product from the PAD File.
        """
        self.version = "1.0.1"

    def _get_published(self):
        """Extract the date of the installer’s publication from the PAD file.
        """
        dt = (datetime.datetime.now()).replace(microsecond=0)
        self.published = dt.isoformat()

    def _get_description(self):
        """Extract the short description of the product (~250 characters).
        """
        self.description = "This dummy module is a trivial example of a " \
                           "Product class implementation. "

    def _get_editor(self):
        """Extract the name of the editor of the product.
        """
        self.editor = "Example. inc"

    def _get_url(self):
        """Extract the url of the current version of the installer
        """
        self.url = "http://www.example.com/index.html"

    def _get_file_size(self):
        """Extract the size of the product installer expressed in bytes
        """
        self.file_size = 0

    def _get_hash(self):
        """Extract the hash value of the product installer (tuple).
        """
        self.hash = None

    def _get_icon(self):
        """Extract the name of the icon file.
        """
        self.icon = None

    def _get_target(self):
        """Extract the target architecture type (the Windows’ one).
        """
        self.target = core.PROD_TARGET_UNIFIED

    def _get_release_note(self):
        """Extract the release note’s URL.
        """
        self.release_note = "http://www.example.com/release_note.txt"

    def _get_std_inst_args(self):
        """Extract the arguments to use for a standard installation.
        """
        self.std_inst_args = ""

    def _get_silent_inst_args(self):
        """Extract the arguments to use for a silent installation.
        """
        self.silent_inst_args = "/slent"
