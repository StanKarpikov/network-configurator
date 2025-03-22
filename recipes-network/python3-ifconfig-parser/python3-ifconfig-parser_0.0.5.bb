SUMMARY = "Unsophisticated python package for parsing raw output of ifconfig."
HOMEPAGE = "https://github.com/KnightWhoSayNi/ifconfig-parser"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://PKG-INFO;md5=86e6349a9072d86ef0e639e183d374cf"

DEPENDS += " python3-setuptools-scm-native"

SRC_URI[md5sum] = "f45d20c2c7d5d7422dd02416d51a5c19"

PYPI_PACKAGE = "ifconfig-parser"

inherit pypi python_setuptools_build_meta