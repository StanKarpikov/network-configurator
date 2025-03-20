const editingFields = new Set();

async function fetchData(url, method = "GET", body = null) {
  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
  };

  if (method === "POST" && body) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    const data = await response.json();

    return {
      status: response.ok,
      response: data,
    };
  } catch (error) {
    console.error("Fetch error:", error);
    return {
      status: false,
      response: error.message,
    };
  }
}

function wifiScanChanged(intf) {
  const selectElement = document.getElementById(`wifi-scan-select-${intf}`);
  const wifiSSID = document.getElementById(`ssid-${intf}`);
  wifiSSID.value = selectElement.value;
}

async function wifiScan(intf) {
  const scanResult = (await fetchData(`/api/param/${intf}/scan`)).response;
  const wifiScanResults = document.getElementById(`scan-list-${intf}`);
  wifiScanResults.innerHTML = "";
  const selectElement = document.createElement("select");
  selectElement.id = `wifi-scan-select-${intf}`;
  selectElement.onchange = () => wifiScanChanged(intf);
  for (const ssid of scanResult) {
    const optionElement = document.createElement("option");
    optionElement.value = ssid;
    optionElement.textContent = ssid;
    selectElement.appendChild(optionElement);
  }
  wifiScanResults.appendChild(selectElement);
}

async function applyConfig(intf, ifaceType) {
  const ip = document.getElementById(`ip-${intf}`).value;
  const mask = document.getElementById(`mask-${intf}`).value;
  const router = document.getElementById(`router-${intf}`).value;
  const connection_type = document.getElementById(`connection-${intf}`).value;

  var data = {
    connection_type: connection_type,
    ip: ip,
    mask: mask,
    route: router,
  };

  if (ifaceType === "wifi") {
    const ssid = document.getElementById(`ssid-${intf}`).value;
    const passphrase = document.getElementById(`passphrase-${intf}`).value;
    data.ssid = ssid;
    data.passphrase = passphrase;
  }
  const { status, response } = await fetchData(
    `/api/${intf}/config`,
    "POST",
    data
  );
  if (!status) {
    const fault = response["error"];
    alert(`Failed to apply configuration: ${fault}`);
  } else {
    alert("Configuration applied successfully");
  }
}

async function loadInterfaces(interfaces, config, status) {
  const container = document.getElementById("interfaces-container");
  container.innerHTML = "";

  for (const intf of interfaces) {
    const ifaceConfig = config[intf] || {};
    const ifaceType = ifaceConfig.type || "undefined";

    let wifiSection = "";
    if (ifaceType === "wifi") {
      wifiSection = `
        <tr>
          <td colspan="2">
            <h4>Available Networks</h4>
            <div id="scan-list-${intf}">(Press scan to show the list of networks)</div>
            <button onclick="wifiScan('${intf}')">Scan</button>
          </td>
        </tr>
        <tr>
          <td>SSID:</td>
          <td><input id="ssid-${intf}" type="text" value="" /></td>
        </tr>
        <tr>
          <td>Password:</td>
          <td><input id="passphrase-${intf}" type="password" value="" /></td>
        </tr>
      `;
    }

    const connectionOptions =
      ifaceType === "wifi"
        ? '<option value="disabled">Disabled</option><option value="station">Station</option><option value="ap">AP</option>'
        : '<option value="disabled">Disabled</option><option value="static_ip">Static IP</option><option value="dynamic_ip">Dynamic IP</option><option value="dhcp">DHCP</option>';

    const ipPattern = "^((25[0-5]|(2[0-4]|1\\d|[1-9]|)\\d)\\.?\\b){4}$";
    container.innerHTML += `
      <div class="interface-block">
        <h3 id="header-${intf}">${intf} - ${ifaceType}</h3>
        <h4 id="status-message-${intf}"></h4>
        <table>
          <tr>
            <td>Connection Type:</td>
            <td>
              <select id="connection-${intf}" onchange="connection_type_changed('${intf}')">
                ${connectionOptions}
              </select>
            </td>
          </tr>
          ${wifiSection}
          <tr>
            <td>IP:</td>
            <td><input class="ip" id="ip-${intf}" type="text" minlength="7" maxlength="15" size="15" pattern="${ipPattern}" value="0.0.0.0" /></td>
          </tr>
          <tr>
            <td>Mask:</td>
            <td><input class="ip" id="mask-${intf}" type="text" minlength="7" maxlength="15" size="15" pattern="${ipPattern}" value="0.0.0.0" /></td>
          </tr>
          <tr>
            <td>Router:</td>
            <td><input class="ip" id="router-${intf}" type="text" minlength="7" maxlength="15" size="15" pattern="${ipPattern}" value="0.0.0.0" /></td>
          </tr>
          <tr>
            <td colspan="2">
              <button onclick="applyConfig('${intf}', '${ifaceType}')">Apply</button>
            </td>
          </tr>
        </table>
      </div>
    `;
  }
}


async function refresh(interfaces, config, status) {
  const container = document.getElementById("interfaces-container");

  const focusedElement = document.activeElement;
  for (const intf of interfaces) {
    const ifaceConfig = config[intf] || {};
    const ifaceType = ifaceConfig.type || "undefined";
    const ifaceConnType = ifaceConfig.connection_type || "disabled";
    const ifaceStatus = status[intf] || {};
    const ifaceStatusError = ifaceStatus.error;
    const ifaceStatusStatus = ifaceStatus.status || "";
    const ifaceStatusMessage = ifaceStatus.message || "";

    document.getElementById(
      `header-${intf}`
    ).innerHTML = `${intf} - ${ifaceType} (${ifaceStatusStatus})`;
    document.getElementById(
      `status-message-${intf}`
    ).innerHTML = `${ifaceStatusMessage}`;
    if (ifaceStatusError) {
      document.getElementById(`status-message-${intf}`).classList.add("error");
    } else {
      document.getElementById(`status-message-${intf}`).classList.remove("error");
    }    

    var edited = false;
    const connection_type = document.getElementById(`connection-${intf}`);
    const ip = document.getElementById(`ip-${intf}`);
    const mask = document.getElementById(`mask-${intf}`);
    const router = document.getElementById(`router-${intf}`);
    if (
      focusedElement === ip ||
      focusedElement === mask ||
      focusedElement === router ||
      focusedElement === connection_type
    ) {
      edited = true;
    }
    if (ifaceType === "wifi") {
      const ssid = document.getElementById(`ssid-${intf}`);
      const passphrase = document.getElementById(`passphrase-${intf}`);
      const ssidSelected = document.getElementById(`wifi-scan-select-${intf}`);
      if (
        focusedElement === ssid ||
        focusedElement === passphrase ||
        focusedElement === ssidSelected
      ) {
        edited = true;
      }
    }

    if (!edited) {
      ip.value = `${ifaceConfig.ip || ""}`;
      mask.value = `${ifaceConfig.mask || ""}`;
      router.value = `${ifaceConfig.route || ""}`;
      connection_type.value = ifaceConnType;
    }
    if (ifaceType === "wifi") {
      const ssid = document.getElementById(`ssid-${intf}`);
      const passphrase = document.getElementById(`passphrase-${intf}`);
      if (!edited) {
        ssid.value = `${ifaceConfig.ssid || ""}`;
        passphrase.value = `${ifaceConfig.passphrase || ""}`;
      }
    }
  }
}

async function connectToWifi(ssid) {
  const password = prompt(`Enter password for ${ssid}`);
  if (password !== null) {
    await fetch(`/api/param/wifi/connect`, {
      method: "POST",
      body: JSON.stringify({ ssid, password }),
    });
    alert(`Connecting to ${ssid}`);
  }
}

async function connectToWifiManual(intf) {
  const ssid = document.getElementById(`ssid-${intf}`).value;
  const password = document.getElementById(`password-${intf}`).value;
  await fetch(`/api/param/${intf}/wifi/connect`, {
    method: "POST",
    body: JSON.stringify({ ssid, password }),
  });
  alert(`Connecting to ${ssid}`);
}

var connected = false;

async function periodicRefresh() {
  const interfaces = (await fetchData("/api/interfaces")).response;
  const config = (await fetchData("/api/config")).response;
  const status = (await fetchData("/api/status")).response;

  if (!connected) {
    if (interfaces && config && status) {
      loadInterfaces(interfaces, config, status);
      refresh(interfaces, config, status);
      connected = true;
    }
  } else {
    if (!config || !status) {
      const container = document.getElementById("interfaces-container");
      container.innerHTML = '<p class="disconnected">Disconnected</p>';
      connected = false;
    }
    refresh(interfaces, config, status);
  }
}

setInterval(periodicRefresh, 2000);
periodicRefresh();
