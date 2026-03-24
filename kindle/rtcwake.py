#!/mnt/us/python/bin/python2.7
"""
rtcwake for Kindle K3 - sets RTC wake alarm via RTC_WKALM_SET ioctl,
then suspends. Bypasses the broken /sys/class/rtc/rtc0/wakealarm sysfs path.

Usage: rtcwake.py <seconds> [mem|standby]
"""
import sys, os, struct, fcntl, time

# ioctl numbers for ARM 32-bit little-endian Linux
# RTC_RD_TIME  = _IOR('p', 0x09, struct rtc_time)   sizeof(rtc_time)=36
# RTC_WKALM_SET= _IOW('p', 0x0f, struct rtc_wkalrm) sizeof(rtc_wkalrm)=40
RTC_RD_TIME   = 0x80247009
RTC_WKALM_SET = 0x4028700f

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: rtcwake.py <seconds> [mem|standby]\n")
        sys.exit(1)

    seconds = int(sys.argv[1])
    mode    = sys.argv[2] if len(sys.argv) > 2 else "mem"

    fd = os.open("/dev/rtc0", os.O_RDONLY)

    # Read current RTC time (struct rtc_time = 9 signed ints)
    buf = ' ' * 36
    buf = fcntl.ioctl(fd, RTC_RD_TIME, buf)
    # (tm_sec, tm_min, tm_hour, tm_mday, tm_mon, tm_year, tm_wday, tm_yday, tm_isdst)

    # Calculate wake time from wall clock + offset, convert to UTC struct tm
    wake = int(time.time()) + seconds
    wt   = time.gmtime(wake)

    # struct rtc_wkalrm:
    #   unsigned char enabled  (1 byte)
    #   unsigned char pending  (1 byte)
    #   2 bytes padding (alignment for following struct rtc_time)
    #   struct rtc_time (9 ints = 36 bytes)
    # Total = 40 bytes
    alarm = struct.pack("BBxx9i",
        1, 0,   # enabled, pending
        wt.tm_sec, wt.tm_min, wt.tm_hour,
        wt.tm_mday, wt.tm_mon - 1, wt.tm_year - 1900,
        wt.tm_wday, wt.tm_yday, -1
    )

    fcntl.ioctl(fd, RTC_WKALM_SET, alarm)
    os.close(fd)

    sys.stderr.write("rtcwake: alarm set +%ds, entering %s\n" % (seconds, mode))
    sys.stderr.flush()

    # Suspend - blocks here until RTC fires and kernel resumes
    pfd = os.open("/sys/power/state", os.O_WRONLY)
    os.write(pfd, mode)
    os.close(pfd)

    sys.stderr.write("rtcwake: resumed\n")

main()
