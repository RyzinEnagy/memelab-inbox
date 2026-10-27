"""Phase 20: bring the loopback interface up inside a fresh network namespace (`unshare -n`), where it starts down and no `ip` tool
exists here. The namespace still has no route out; only 127.0.0.1 works. Used by fresh_env.sh for the loopback mock services of the
Phase 14 tests (finding F20-11)."""
import fcntl, socket, struct
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
flags = struct.unpack("16sh", fcntl.ioctl(s, 0x8913, struct.pack("16sh", b"lo", 0)))[1]
fcntl.ioctl(s, 0x8914, struct.pack("16sh", b"lo", flags | 0x1))
print("lo up")
