SUMMARY = "Network Configurator"
LICENSE = "CLOSED"

DEPENDS = " python3-nmcli \
            python3-ifconfig-parser \
            python3-netaddr \
            "

inherit systemd pkgconfig

SYSTEMD_PACKAGES += "${PN}"
SYSTEMD_AUTO_ENABLE:${PN} = "disable"
SYSTEMD_SERVICE:${PN} = "network-configurator.service"

FILESEXTRAPATHS:prepend = "${THISDIR}/files:"
SRC_URI = " \
    file://source/ \
    file://network-configurator.service \
    "

do_install:append() {
    install -d "${D}/usr/local/network-configurator/"
    
    cp -R --no-dereference --preserve=mode,links -v ${WORKDIR}/source/src/* "${D}/usr/local/network-configurator/"
    chmod 0744 -R "${D}/usr/local/network-configurator/"

    install -d ${D}/${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/network-configurator.service ${D}/${systemd_unitdir}/system/

    install -d -m 0710 "${D}/etc/sudoers.d"

    # TODO: Make the rules less broad
    echo "${ST_CONTROL_USER_NAME} ALL=(ALL) NOPASSWD: /usr/bin/nmcli*, /usr/bin/iw*, /usr/bin/ip*, /usr/bin/ifconfig*, /usr/bin/sysctl -w net.ipv4.ip_forward*" > "${D}/etc/sudoers.d/0001_netw_conf"
    chmod 0644 "${D}/etc/sudoers.d/0001_netw_conf"
}

FILES:${PN} = " /usr/local/network-configurator/ \
                ${systemd_unitdir}/system/network-configurator.service \
                /etc/sudoers.d \
                /etc/sudoers.d/0001_netw_conf"