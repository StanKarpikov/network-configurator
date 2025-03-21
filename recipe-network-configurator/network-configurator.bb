do_install () {
    install -d -m 0710 "${D}/etc/sudoers.d"
    echo "${ST_CONTROL_USER_NAME} ALL=(ALL) NOPASSWD: /usr/bin/nmcli*, /usr/bin/iw*, /usr/bin/ip*, /usr/bin/ifconfig*, /usr/bin/sysctl -w net.ipv4.ip_forward*, /usr/bin/killall dnsmasq, /usr/bin/killall hostapd" > "${D}/etc/sudoers.d/0001_netw_conf_${ST_CONTROL_USER_NAME}"
    chmod 0644 "${D}/etc/sudoers.d/0002_${ST_CONTROL_USER_NAME}"
}

FILES_${PN} +=  "/etc/sudoers.d \
                 /etc/sudoers.d/0001_netw_conf_${ST_CONTROL_USER_NAME}"