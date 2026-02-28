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
