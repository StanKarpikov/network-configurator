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

function createWifiList(wifiNetworks) {
  return wifiNetworks.map(network => `
    <div class="wifi-item">
      <span>${network.ssid} (Signal: ${network.signal}%)</span>
      <button onclick="connectToWifi('${network.ssid}')">Connect</button>
    </div>
  `).join('');
}

function validateIP(ip) {
  const regex = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(\1)\.(\1)\.(\1)$/;
  return regex.test(ip);
}

async function wifiScan(interfaceName) {
    const scanResult = await fetchData(`/api/param/${interfaceName}/scan`);
    const wifiScanResults = document.getElementById(`scan-list-${interfaceName}`);

    wifiScanResults.innerHTML = '';

    const selectElement = document.createElement('select');

    for (const ssid of scanResult) {
        const optionElement = document.createElement('option');
        optionElement.value = ssid;
        optionElement.textContent = ssid;
        selectElement.appendChild(optionElement);
    }

    wifiScanResults.appendChild(selectElement);
}

async function applyConfig(interfaceName) {
  const ip = document.getElementById(`ip-${interfaceName}`).value;
  const mask = document.getElementById(`mask-${interfaceName}`).value;
  const router = document.getElementById(`router-${interfaceName}`).value;

  if (!validateIP(ip) || !validateIP(mask) || !validateIP(router)) {
    alert('Invalid IP, Mask, or Router address. Please check again.');
    return;
  }

  const data = { ip, mask, router };
  await fetch(`/api/param/${interfaceName}/config`, { method: 'POST', body: JSON.stringify(data) });
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

    container.innerHTML += `
      <div class="interface-block">
        <h3 id="header-${intf}">${intf} - ${ifaceType}</h3>
        <p id="status-message-${intf}"></p>
        <label>Connection Type: <select id="connection-${intf}">${connectionOptions}</select></label>
        ${wifiSection}
        <label>IP: <input id="ip-${intf}" type="text" value="0.0.0.0" /></label>
        <label>Mask: <input id="mask-${intf}" type="text" value="0.0.0.0" /></label>
        <label>Router: <input id="router-${intf}" type="text" value="0.0.0.0" /></label>
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
        if(focusedElement === ssid || focusedElement === passphrase)
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

async function connectToWifiManual(interfaceName) {
  const ssid = document.getElementById(`ssid-${interfaceName}`).value;
  const password = document.getElementById(`password-${interfaceName}`).value;
  await fetch(`/api/param/${interfaceName}/wifi/connect`, { method: 'POST', body: JSON.stringify({ ssid, password }) });
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