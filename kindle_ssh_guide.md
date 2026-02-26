## Shortcut — SSH Config (Optional)

### Windows
```
Host kindle
    HostName <KINDLE_IP_ADDRESS>
    User root
    IdentityFile C:\path\to\your\kindle\private_key.pem
```

### Linux/macOS/WSL
```
Host kindle
    HostName <KINDLE_IP_ADDRESS>
    User root
    IdentityFile ~/.path/to/your/kindle/private_key.pem
```

*Replace <KINDLE_IP_ADDRESS> with the actual IP address of your Kindle device.*