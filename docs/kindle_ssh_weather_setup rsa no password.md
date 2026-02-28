# Kindle Weather: SSH + systemd setup (Ubuntu → Kindle) — Reference & Cleanup

This document captures the final working setup (as of **2026-02-28**) for running a weather updater on an Amazon Kindle over USBNetwork SSH from an Ubuntu machine, plus notes on gotchas and cleanup.

## Goal

- Ubuntu runs a daemon (systemd user service) that periodically:
  - fetches weather JSON
  - pushes the JSON to the Kindle
  - triggers the Kindle to render/update

Hard requirement: **passwordless SSH from Ubuntu → Kindle** (so the daemon is unattended).

---

## Final working SSH configuration

### Working key type

Use an **ED25519 user key** from Ubuntu. (RSA ran into signature-algorithm compatibility issues with OpenSSH_7.0 on the Kindle and modern OpenSSH clients.)

Ubuntu key used:

- Private: `~/.ssh/kindle_ed25519_2026`
- Public:  `~/.ssh/kindle_ed25519_2026.pub`

### Ubuntu `~/.ssh/config`

This ensures both `ssh kindle` **and** `ssh root@10.45.69.239` work.

```sshconfig
Host 10.45.69.239
  User root
  IdentityFile ~/.ssh/kindle_ed25519_2026
  IdentitiesOnly yes
  PreferredAuthentications publickey
  ServerAliveInterval 30
  ServerAliveCountMax 3

Host kindle
  HostName 10.45.69.239
  User root
  IdentityFile ~/.ssh/kindle_ed25519_2026
  IdentitiesOnly yes
  PreferredAuthentications publickey
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

### Verification command (Ubuntu)

Must succeed without prompting:

```bash
ssh -o BatchMode=yes kindle 'echo OK_FROM_KINDLE'
```

Expected output:

```text
OK_FROM_KINDLE
```

---

## Kindle-side SSH authorized keys (important gotcha)

### What we expected

We configured Kindle OpenSSH with:

```text
AuthorizedKeysFile /mnt/us/usbnet/etc/.ssh/authorized_keys
```

and the file exists:

- `/mnt/us/usbnet/etc/.ssh/authorized_keys`

### What actually mattered (observed via `sshd -ddd`)

In debugging mode, `sshd` attempted to open:

- `/mnt/us/usbnet/etc/authorized_keys`

and failed until that file existed.

Therefore we keep the key in:

- **`/mnt/us/usbnet/etc/authorized_keys`**  ← *critical for real auth on this device*

Current Kindle files (as observed):

- `/mnt/us/usbnet/etc/authorized_keys` (contains ED25519 key, 103 bytes)
- `/mnt/us/usbnet/etc/.ssh/authorized_keys` (also present)

Recommendation: keep **both** files containing the same public key for redundancy.

### Confirm key fingerprint on Kindle

```sh
/mnt/us/usbnet/bin/ssh-keygen -lf /mnt/us/usbnet/etc/authorized_keys
```

Should match Ubuntu:

```sh
ssh-keygen -lf ~/.ssh/kindle_ed25519_2026.pub
```

---

## Kindle `sshd_config` (usbnet)

Current tail section (key authentication enabled):

```text
# --- Kindle weather: key auth from /mnt/us (usbnet) ---
PubkeyAuthentication yes
AuthorizedKeysFile /mnt/us/usbnet/etc/.ssh/authorized_keys
PermitRootLogin yes
StrictModes no
PasswordAuthentication yes
```

Notes:
- `/mnt/us` is typically VFAT-like with odd permissions; `StrictModes no` is important.
- Even with the above, this Kindle still required `/mnt/us/usbnet/etc/authorized_keys` to exist for successful key auth (per debug output).

---

## systemd user service (Ubuntu)

Service file path:

- `~/.config/systemd/user/kindle-weather.service`

Current contents:

```ini
[Unit]
Description=Kindle Weather Updater (push JSON + trigger Kindle render)

[Service]
ExecStart=%h/kindle-weather/kindle_weather_daemon.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Useful commands:

```bash
# restart
systemctl --user restart kindle-weather.service

# logs
journalctl --user -u kindle-weather.service -n 100 --no-pager

# enable at login/boot (user session)
systemctl --user enable kindle-weather.service
```

If you want this to run even when not logged in, you may need user lingering:

```bash
loginctl enable-linger "$USER"
```

---

## Windows note (host key warning)

If connecting from Windows and you see:

> WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!

Fix by removing the old key entry:

```powershell
ssh-keygen -R 10.45.69.239
```

Then reconnect and accept the new fingerprint.

---

## Cleanup (what to keep / what you can remove)

### Ubuntu `~/.ssh` key files observed

Present:

- `kindle_ed25519` (older)
- `kindle_ed25519.pub` (older)
- `kindle_ed25519_2026` (current, used)
- `kindle_ed25519_2026.pub` (current, used)
- `kindle_rsa` + `kindle_rsa.pub` (old RSA)
- `kindle_rsa_2048` + `kindle_rsa_2048.pub` (RSA 2048)

#### Keep (required)

- `~/.ssh/kindle_ed25519_2026`
- `~/.ssh/kindle_ed25519_2026.pub`
- `~/.ssh/config`

#### Optional removals (safe if you don’t need fallback)

If everything is stable with ED25519, you can remove the older unused keys:

```bash
rm -f ~/.ssh/kindle_rsa ~/.ssh/kindle_rsa.pub
rm -f ~/.ssh/kindle_rsa_2048 ~/.ssh/kindle_rsa_2048.pub
rm -f ~/.ssh/kindle_ed25519 ~/.ssh/kindle_ed25519.pub
```

(Keep them if you want extra fallback options.)

### Kindle files to keep

Keep:

- `/mnt/us/usbnet/etc/authorized_keys`  (**required** on this device)
- `/mnt/us/usbnet/etc/.ssh/authorized_keys` (recommended redundancy)
- `/mnt/us/usbnet/etc/sshd_config`

Optional: if any temporary pubkey files were created under `/mnt/us/usbnet/etc/*.pub`, they can be removed after confirming auth works. (In our final state, only the authorized_keys files matter.)

---

## Quick “everything is healthy” checklist

On Ubuntu:

```bash
ssh -o BatchMode=yes kindle 'echo OK'
systemctl --user restart kindle-weather.service
journalctl --user -u kindle-weather.service -n 30 --no-pager
```

On Kindle:

```sh
/mnt/us/usbnet/bin/ssh-keygen -lf /mnt/us/usbnet/etc/authorized_keys
```

---

## Troubleshooting tip (most definitive)

If key auth ever breaks again, the fastest way to see *why* is to temporarily run:

```sh
/mnt/us/usbnet/sbin/sshd -D -ddd -4 -p 22 -f /mnt/us/usbnet/etc/sshd_config
```

Then attempt a login from Ubuntu and watch which `authorized_keys` path sshd tries to open and why it refuses/accepts the key.

(Remember to restart normal sshd afterward by toggling usbnetwork.)

## From scratch: set up ED25519 key auth (Ubuntu → Kindle)

### 1) Generate a dedicated key on Ubuntu
```bash
ssh-keygen -t ed25519 -f ~/.ssh/kindle_ed25519_2026 -N ""
```

### 2) Install the public key on the Kindle (password once)
Copy the pubkey to the Kindle:

```bash
scp ~/.ssh/kindle_ed25519_2026.pub root@10.45.69.239:/mnt/us/usbnet/etc/kindle_ed25519_2026.pub
```

Install it into the location `sshd` actually reads on this device:

```bash
ssh root@10.45.69.239 'cat /mnt/us/usbnet/etc/kindle_ed25519_2026.pub > /mnt/us/usbnet/etc/authorized_keys && sync'
```

(Optional redundancy: also write it to the `.ssh/` path)

```bash
ssh root@10.45.69.239 'mkdir -p /mnt/us/usbnet/etc/.ssh; cat /mnt/us/usbnet/etc/kindle_ed25519_2026.pub > /mnt/us/usbnet/etc/.ssh/authorized_keys && sync'
```

### 3) Configure Ubuntu SSH to use the key
Edit `~/.ssh/config` and add:

```sshconfig
Host kindle
  HostName 10.45.69.239
  User root
  IdentityFile ~/.ssh/kindle_ed25519_2026
  IdentitiesOnly yes
  PreferredAuthentications publickey
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

(Optional: make `ssh root@10.45.69.239` also use the key)

```sshconfig
Host 10.45.69.239
  User root
  IdentityFile ~/.ssh/kindle_ed25519_2026
  IdentitiesOnly yes
  PreferredAuthentications publickey
```

### 4) Verify passwordless login
```bash
ssh -o BatchMode=yes kindle 'echo OK_FROM_KINDLE'
```

Expected:
```text
OK_FROM_KINDLE
```

### 5) Disable password auth (optional hardening)
Only do this after you’ve verified BatchMode works.

In `/mnt/us/usbnet/etc/sshd_config` set:
```text
PasswordAuthentication no
```

Then restart sshd (usbnetwork toggle twice).
