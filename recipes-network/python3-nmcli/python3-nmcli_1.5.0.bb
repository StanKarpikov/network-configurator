SUMMARY = "A python wrapper library for the network-manager cli client"
HOMEPAGE = "https://github.com/ushiboy/nmcli"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://PKG-INFO;md5=9d853eda7d9bbdaf930332aadfab2e8f"

DEPENDS += " python3-setuptools-scm-native"

SRC_URI[md5sum] = "22a13f37bd96d1fbdb7dba97383eb7d9"

PYPI_PACKAGE = "nmcli"

inherit pypi python_setuptools_build_meta