# Kindle Keyboard Wi-Fi (K3W) — Jailbreak & SSH over Wi-Fi Guide

**Device:** Kindle Keyboard Wi-Fi (model `B008`, 3rd gen)  
**Goal:** Root shell access over Wi-Fi via SSH  
**Host OS:** Windows (PowerShell) — notes for Linux/Ubuntu included where relevant

---

## Prerequisites — Files Needed

Download these from [MobileRead](https://www.mobileread.com/forums/showthread.php?t=88004) and [NiLuJe's USBNetwork thread](https://www.mobileread.com/forums/showthread.php?t=88004):

| File | Purpose |
|------|---------|
| [kindle-jailbreak-0.13.N.zip](file:///C:/Users/am71/Downloads/kindle-jailbreak-0.13.N.zip) | Jailbreak for K3 |
| [kindle-usbnetwork-0.57.N-k3.zip](file:///c:/Users/am71/Downloads/kindle-usbnetwork-0.57.N-k3.zip) | USBNetwork hack for K3 |

---

## Step 1 — Jailbreak the Kindle

1. Extract [kindle-jailbreak-0.13.N.zip](file:///C:/Users/am71/Downloads/kindle-jailbreak-0.13.N.zip).
2. Inside, find **[Update_jailbreak_0.13.N_k3w_install.bin](file:///C:/Users/am71/Desktop/Antigravity/kindle/jailbreak/Update_jailbreak_0.13.N_k3w_install.bin)** (the `k3w` variant is for Kindle Keyboard Wi-Fi).
3. Connect the Kindle via USB — it mounts as a drive.
4. Copy the [.bin](file:///C:/Users/am71/Desktop/Antigravity/kindle/jailbreak/Update_jailbreak_0.13.N_k2_install.bin) file to the **root** of the Kindle drive (not into any folder).
5. On the Kindle: **Home → Menu → Settings → Menu → Update Your Kindle**.
6. Wait for it to reboot. You should see **"Update Successful"**.

---

## Step 2 — Install USBNetwork Hack

1. Extract [kindle-usbnetwork-0.57.N-k3.zip](file:///c:/Users/am71/Downloads/kindle-usbnetwork-0.57.N-k3.zip).
2. Inside, find **[Update_usbnetwork_0.57.N_k3w_install.bin](file:///C:/Users/am71/Desktop/Antigravity/kindle/usbnetwork/Update_usbnetwork_0.57.N_k3w_install.bin)**.
3. Connect the Kindle via USB again.
4. Copy the [.bin](file:///C:/Users/am71/Desktop/Antigravity/kindle/jailbreak/Update_jailbreak_0.13.N_k2_install.bin) to the **root** of the Kindle drive.
5. On the Kindle: **Home → Menu → Settings → Menu → Update Your Kindle**.
6. Wait for reboot. You should see **"Update Successful"**.

After this step, the Kindle drive will contain a new **[usbnet/](file:///C:/Users/am71/Desktop/Antigravity/kindle/usbnet022/USBNetwork/src/usbnet/bin/usbnetwork#230-369)** folder.

---

## Step 3 — Configure Wi-Fi SSH

With the Kindle still connected via USB, edit [usbnet/etc/config](file:///D:/usbnet/etc/config).

Find and change these two lines:

```sh
# Before:
K3_WIFI="false"
K3_WIFI_SSHD_ONLY="false"

# After:
K3_WIFI="true"
K3_WIFI_SSHD_ONLY="true"
```

> **⚠️ CRITICAL:** This file MUST have **UNIX line endings** (`\n` only, no `\r\n`).  
> If editing on Windows, use a tool like VS Code (set EOL to LF) or run this Python snippet:
> ```python
> with open(r"D:\usbnet\etc\config", "rb") as f:
>     data = f.read()
> with open(r"D:\usbnet\etc\config", "wb") as f:
>     f.write(data.replace(b"\r\n", b"\n"))
> ```

---

## Step 4 — Add Your SSH Public Key

Generate an SSH key pair on your computer (skip if you already have one):

```bash
# Linux/macOS/WSL
ssh-keygen -t rsa -b 2048 -f ~/.ssh/kindle_rsa

# Windows PowerShell — hit Enter twice for no passphrase
ssh-keygen -t rsa -b 2048 -f C:\Users\YourName\.ssh\kindle_rsa
```

Copy the **public key** (`kindle_rsa.pub`) into the Kindle's [usbnet/etc/authorized_keys](file:///D:/usbnet/etc/authorized_keys) file.

> **⚠️ CRITICAL:** This file also must use **UNIX line endings**. Write it with Python to be safe:
> ```python
> pubkey = open("C:/Users/YourName/.ssh/kindle_rsa.pub", "rb").read().strip()
> with open(r"D:\usbnet\etc\authorized_keys", "wb") as f:
>     f.write(pubkey + b"\n")
> ```

---

## Step 5 — Find the Kindle's IP Address

The quickest method: set up a temporary HTTP server on your PC, then open the URL on the Kindle's experimental browser — the server log will reveal the Kindle's IP.

**On your PC**, find your local IP first:
```powershell
# Windows
ipconfig | findstr "IPv4"
```

Then start a server (e.g., your local IP is `10.45.69.132`):
```bash
python -m http.server 8000
```

**On the Kindle:** Open the experimental browser → go to `http://10.45.69.132:8000`.  
Check the server terminal — the Kindle's IP will appear in the log, e.g.:
```
::ffff:10.45.69.239 - - [26/Feb/2026] "GET / HTTP/1.1" 200 -
```

Keep note of this IP (e.g., `10.45.69.239`).

> **Tip:** Set a DHCP reservation for the Kindle's MAC address in your router so the IP never changes.

---

## Step 6 — Enable SSH on the Kindle

1. **Safely eject** the Kindle from your PC and unplug the USB cable.
2. Wait ~10 seconds for it to reconnect to Wi-Fi.
3. On the Kindle's Home screen, open the search bar and type:
   ```
   ;debugOn
   ```
   Press Enter (nothing visible happens — that's fine, debug mode is now on).
4. Open the search bar again and type:
   ```
   ~usbNetwork
   ```
   Press Enter. The SSH daemon will start in the background.

> **Note:** `~usbNetwork` is a toggle. Running it again stops SSH. `;debugOn` stays active until the Kindle reboots.

---

## Step 7 — SSH In

From your PC:

```bash
# Linux/macOS (using the key we set up)
ssh -i ~/.ssh/kindle_rsa root@10.45.69.239

# Windows PowerShell — requires an extra flag because the Kindle runs
# an old Dropbear (2015) that only supports legacy ssh-rsa SHA-1 signatures,
# which modern OpenSSH 8.8+ disables by default:
ssh -o PubkeyAcceptedKeyTypes=ssh-rsa -o PubkeyAcceptedAlgorithms=ssh-rsa -i C:\Users\YourName\.ssh\kindle_rsa root@10.45.69.239
```

You should be greeted with:
```
Welcome to Kindle!

root@10.45.69.239:~#
```

---

## Shortcut — SSH Config (Optional)

To make this permanent so you can just type `ssh kindle`, add this to `~/.ssh/config` (or `C:\Users\YourName\.ssh\config` on Windows):

```
Host kindle
    HostName 10.45.69.239
    User root
    IdentityFile ~/.ssh/kindle_rsa
    PubkeyAcceptedKeyTypes ssh-rsa
    PubkeyAcceptedAlgorithms ssh-rsa
    StrictHostKeyChecking no
```

Then simply:
```bash
ssh kindle
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `;un` takes you to a blank search page | Wrong command for K3 firmware | Use `;debugOn` then `~usbNetwork` |
| Port 22 refuses connection | SSH service not started, or toggled off | Re-run `~usbNetwork` once on the Kindle |
| `Permission denied (publickey,password)` | Key mismatch or wrong [authorized_keys](file:///D:/usbnet/etc/authorized_keys) | Verify the public key in [authorized_keys](file:///D:/usbnet/etc/authorized_keys) matches your private key |
| `send_pubkey_test: no mutual signature algorithm` | Modern OpenSSH vs old Dropbear 2015 | Add `-o PubkeyAcceptedKeyTypes=ssh-rsa -o PubkeyAcceptedAlgorithms=ssh-rsa` |
| Wrong password for root | Default password is derived from serial number | Use SSH keys instead (recommended) |
| SSH key rejected (Windows `\r\n` endings) | Windows tools wrote CRLF to the files | Re-write both [config](file:///D:/usbnet/etc/config) and [authorized_keys](file:///D:/usbnet/etc/authorized_keys) using Python `open(..., "wb")` |
