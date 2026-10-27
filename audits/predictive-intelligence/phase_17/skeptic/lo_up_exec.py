"""Inside `unshare -n`: bring the loopback interface up (no route out exists), then exec the given command."""
import fcntl, os, socket, struct, sys
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ifr = struct.pack("16sH14s", b"lo", 0x1 | 0x40, b"\x00" * 14)  # IFF_UP | IFF_RUNNING
fcntl.ioctl(s.fileno(), 0x8914, ifr)  # SIOCSIFFLAGS
os.execvp(sys.argv[1], sys.argv[1:])
