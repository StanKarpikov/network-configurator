const editingFields = new Set();

async function fetchData(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Fetch failed');
    return response.json();
  } catch (error) {
    return null;
  }
}

function wifiScanChanged(intf)
{
    const selectElement = document.getElementById(`wifi-scan-select-${intf}`);
    const wifiSSID = document.getElementById(`ssid-${intf}`);
    wifiSSID.value = selectElement.value;
}

async function wifiScan(intf) {
    const scanResult = await fetchData(`/api/param/${intf}/scan`);
    const wifiScanResults = document.getElementById(`scan-list-${intf}`);
    wifiScanResults.innerHTML = '';
    const selectElement = document.createElement('select');
    selectElement.id=`wifi-scan-select-${intf}`;
    selectElement.onchange = () => wifiScanChanged(intf);
    for (const ssid of scanResult) {
        const optionElement = document.createElement('option');
        optionElement.value = ssid;
        optionElement.textContent = ssid;
        selectElement.appendChild(optionElement);
    }
    wifiScanResults.appendChild(selectElement);
}

async function applyConfig(intf) {
  const ip = document.getElementById(`ip-${intf}`).value;
  const mask = document.getElementById(`mask-${intf}`).value;
  const router = document.getElementById(`router-${intf}`).value;

  const data = { ip, mask, router };
  await fetch(`/api/param/${intf}/config`, { method: 'POST', body: JSON.stringify(data) });
  alert('Configuration applied successfully.');
}

async function loadInterfaces(interfaces, config, status)
{
  const container = document.getElementById('interfaces-container');
  container.innerHTML = '';

  for (const intf of interfaces)
  {
    const ifaceConfig = config[intf] || {};
    const ifaceType = ifaceConfig.type || "undefined";

    let wifiSection = '';
    if (ifaceType === 'wifi') {
      wifiSection = `
        <div class="wifi-list">
          <h4>Available Networks</h4>
          <div id="scan-list-${intf}"></div>
        </div>
        <button onclick="wifiScan('${intf}')">Scan</button>
        <label>SSID: <input id="ssid-${intf}" type="text" value="" /></label>
        <label>Password: <input id="passphrase-${intf}" type="password" value="" /></label>
      `;
    }

    const connectionOptions = ifaceType === 'wifi'
              ? '<option value="disabled">Disabled</option><option value="station">Station</option><option value="ap">AP</option>'
              : '<option value="disabled">Disabled</option><option value="static_ip">Static IP</option><option value="dynamic_ip">Dynamic IP</option><option value="dhcp">DHCP</option>';

    const ipPattern = "^((25[0-5]|(2[0-4]|1\\d|[1-9]|)\\d)\\.?\\b){4}$"
    container.innerHTML += `
      <div class="interface-block">
        <h3 id="header-${intf}">${intf} - ${ifaceType}</h3>
        <p id="status-message-${intf}"></p>
        <label>Connection Type: <select id="connection-${intf}" onchange="connection_type_changed('${intf}')" >${connectionOptions}</select></label>
        ${wifiSection}
        <label>IP: <input class="ip" id="ip-${intf}" type="text" minlength="7" maxlength="15" size="15" pattern="${ipPattern}" value="0.0.0.0" /></label>
        <label>Mask: <input class="ip" id="mask-${intf}" type="text" minlength="7" maxlength="15" size="15" pattern="${ipPattern}" value="0.0.0.0" /></label>
        <label>Router: <input class="ip" id="router-${intf}" type="text" minlength="7" maxlength="15" size="15" pattern="${ipPattern}" value="0.0.0.0" /></label>
        <button onclick="applyConfig('${intf}')">Apply</button>
      </div>
    `;
  }
}

async function refresh(interfaces, config, status) {
  const container = document.getElementById('interfaces-container');

  const focusedElement = document.activeElement;
  for (const intf of interfaces)
  {
    const ifaceConfig = config[intf] || {};
    const ifaceType = ifaceConfig.type || "undefined";
    const ifaceConnType = ifaceConfig.connection_type || "disabled";
    const ifaceStatus = status[intf] || {};
    const ifaceStatusError = ifaceStatus.error;
    const ifaceStatusStatus = ifaceStatus.status || "";
    const ifaceStatusMessage = ifaceStatus.message || "";

    document.getElementById(`header-${intf}`).innerHTML = `${intf} - ${ifaceType} (${ifaceStatusStatus})`;
    document.getElementById(`status-message-${intf}`).innerHTML = `${ifaceStatusMessage}`;
    if(ifaceStatusError)
    {
        document.getElementById(`status-message-${intf}`).class = "error"
    }
    else
    {
        document.getElementById(`status-message-${intf}`).class = ""
    }

    var edited = false;
    const connection_type = document.getElementById(`connection-${intf}`);
    const ip = document.getElementById(`ip-${intf}`);
    const mask = document.getElementById(`mask-${intf}`);
    const router = document.getElementById(`router-${intf}`);
    if(focusedElement === ip || focusedElement === mask || focusedElement === router || focusedElement === connection_type)
    {
        edited = true;
    }
    if (ifaceType === 'wifi')
    {
        const ssid = document.getElementById(`ssid-${intf}`);
        const passphrase =document.getElementById(`passphrase-${intf}`);
        const ssidSelected = document.getElementById(`wifi-scan-select-${intf}`);
        if(focusedElement === ssid || focusedElement === passphrase || focusedElement === ssidSelected)
        {
            edited = true;
        }
    }

    if(!edited)
    {
        ip.value = `${ifaceConfig.ip || ''}`;
        mask.value = `${ifaceConfig.mask || ''}`;
        router.value = `${ifaceConfig.route || ''}`;
        connection_type.value = ifaceConnType;
    }
    if (ifaceType === 'wifi')
    {
        const ssid = document.getElementById(`ssid-${intf}`);
        const passphrase = document.getElementById(`passphrase-${intf}`);
        if(!edited)
        {
            ssid.value = `${ifaceConfig.ssid || ''}`;
            passphrase.value = `${ifaceConfig.passphrase || ''}`;
        }
    }
  }
}

async function connectToWifi(ssid) {
  const password = prompt(`Enter password for ${ssid}`);
  if (password !== null) {
    await fetch(`/api/param/wifi/connect`, { method: 'POST', body: JSON.stringify({ ssid, password }) });
    alert(`Connecting to ${ssid}`);
  }
}

async function connectToWifiManual(intf) {
  const ssid = document.getElementById(`ssid-${intf}`).value;
  const password = document.getElementById(`password-${intf}`).value;
  await fetch(`/api/param/${intf}/wifi/connect`, { method: 'POST', body: JSON.stringify({ ssid, password }) });
  alert(`Connecting to ${ssid}`);
}

var connected = false;

async function periodicRefresh()
{
  const interfaces = await fetchData('/api/interfaces');
  const config = await fetchData('/api/config');
  const status = await fetchData('/api/status');

  if(!connected)
  {
      if (interfaces && config && status) {
        loadInterfaces(interfaces, config, status);
        refresh(interfaces, config, status);
        connected = true;
      }
  }
  else
  {
      if (!config || !status) {
        const container = document.getElementById('interfaces-container');
        container.innerHTML = '<p class="disconnected">Disconnected</p>';
        connected = false;
      }
      refresh(interfaces, config, status);
  }
}

setInterval(periodicRefresh, 2000);
periodicRefresh();