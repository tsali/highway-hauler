"""
rlogin → Evennia telnet bridge for Highway Hauler.

Usage:
    python bridge.py <listen_port> <evennia_telnet_port>

Adapted from Kayfabe bridge. Mystic BBS connects via rlogin (RFC 1282).
This bridge:
  1. Performs the rlogin handshake to extract the BBS username.
  2. Responds with \x00 (rlogin OK).
  3. Connects to Evennia's telnet port.
  4. Automates login using Evennia 5.x command-based login:
       connect <username> <password>        (existing account)
       create <username> <password> + Y     (new account, then connect)
  5. Bridges the session bidirectionally once logged in.

The shared secret password is BRIDGE_PASSWORD below. It must match
BBS_BRIDGE_PASSWORD in the Evennia settings.py.

Evennia 5.x login response strings:
  Banner ends with: "Enter help for more info."
  Connect success:  "You become"
  Connect failure:  "Username and/or password is incorrect."
  Create confirm:   "[Y]/N?"
"""

import asyncio
import logging
import re
import sys

BRIDGE_PASSWORD = "pepsicola_bbs_secret_2026"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [hauler-bridge] %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("bridge")


def parse_rlogin_header(data: bytes):
    """Parse rlogin handshake. Returns (client_user, server_user) or None."""
    if not data or data[0] != 0:
        return None
    fields = data[1:].split(b"\x00")
    if len(fields) < 3:
        return None
    client_user = fields[0].decode("ascii", errors="replace").strip()
    server_user = fields[1].decode("ascii", errors="replace").strip()
    return client_user, server_user


def strip_ansi_iac(data: bytes) -> str:
    """Strip Telnet IAC sequences and ANSI codes, return clean text."""
    data = re.sub(b"\xff[\xfb-\xfe].", b"", data)
    data = re.sub(b"\xff.", b"", data)
    data = re.sub(b"\x1b\\[[^m]*m", b"", data)
    data = re.sub(b"\x1b\\[[^a-zA-Z]*[a-zA-Z]", b"", data)
    return data.decode("utf-8", errors="replace")


async def read_until_pattern(reader, pattern, timeout=15.0):
    """Read until pattern found in clean text. Returns raw bytes."""
    raw_buf = b""
    clean_buf = ""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise asyncio.TimeoutError(f"Timed out waiting for {pattern!r}; got: {clean_buf[-200:]!r}")
        try:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=min(remaining, 1.0))
        except asyncio.TimeoutError:
            continue
        if not chunk:
            raise ConnectionError(f"Connection closed waiting for {pattern!r}")
        raw_buf += chunk
        clean_buf += strip_ansi_iac(chunk)
        if pattern in clean_buf:
            return raw_buf


async def read_until_any(reader, patterns, timeout=15.0):
    """Read until any pattern found. Returns (raw_bytes, matched_pattern)."""
    raw_buf = b""
    clean_buf = ""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise asyncio.TimeoutError(f"Timed out waiting for any of {patterns!r}; got: {clean_buf[-200:]!r}")
        try:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=min(remaining, 1.0))
        except asyncio.TimeoutError:
            continue
        if not chunk:
            raise ConnectionError(f"Connection closed waiting for any of {patterns!r}")
        raw_buf += chunk
        clean_buf += strip_ansi_iac(chunk)
        for p in patterns:
            if p in clean_buf:
                return raw_buf, p


UNICODE_TO_ASCII = [
    (b"\xe2\x80\x94", b"--"),
    (b"\xe2\x80\x93", b"-"),
    (b"\xe2\x80\x98", b"'"),
    (b"\xe2\x80\x99", b"'"),
    (b"\xe2\x80\x9c", b'"'),
    (b"\xe2\x80\x9d", b'"'),
    (b"\xe2\x80\xa6", b"..."),
    (b"\xe2\x80\xa2", b"*"),
    (b"\xc2\xa0", b" "),
]


def transliterate_for_bbs(data: bytes) -> bytes:
    for utf8_seq, ascii_rep in UNICODE_TO_ASCII:
        data = data.replace(utf8_seq, ascii_rep)
    return data


_RE_ANSI = re.compile(rb"\x1b\[[^a-zA-Z]*[a-zA-Z]")


def wordwrap_ansi(data: bytes, width: int = 78) -> bytes:
    """Word-wrap text at `width` visible columns, preserving ANSI codes."""
    lines = data.split(b"\r\n")
    out = []
    for line in lines:
        visible = _RE_ANSI.sub(b"", line)
        if len(visible) <= width:
            out.append(line)
            continue
        result_lines = []
        current = bytearray()
        vis_len = 0
        last_space_pos = -1
        last_space_vis = 0
        i = 0
        while i < len(line):
            if line[i:i+1] == b"\x1b" and i + 1 < len(line) and line[i+1:i+2] == b"[":
                j = i + 2
                while j < len(line) and not (0x41 <= line[j] <= 0x5A or 0x61 <= line[j] <= 0x7A):
                    j += 1
                if j < len(line):
                    j += 1
                current.extend(line[i:j])
                i = j
                continue
            byte = line[i:i+1]
            if byte == b" ":
                last_space_pos = len(current)
                last_space_vis = vis_len
            current.extend(byte)
            vis_len += 1
            i += 1
            if vis_len >= width:
                if last_space_pos > 0:
                    result_lines.append(bytes(current[:last_space_pos]))
                    current = bytearray(current[last_space_pos + 1:])
                    vis_len = vis_len - last_space_vis - 1
                else:
                    result_lines.append(bytes(current))
                    current = bytearray()
                    vis_len = 0
                last_space_pos = -1
                last_space_vis = 0
        if current:
            result_lines.append(bytes(current))
        out.extend(result_lines)
    return b"\r\n".join(out)


def process_iac_from_server(data: bytes):
    """Process Telnet IAC sequences. Returns (clean_data, responses)."""
    clean = bytearray()
    replies = bytearray()
    IAC, WILL, WONT, DO, DONT = 0xFF, 0xFB, 0xFC, 0xFD, 0xFE
    SGA = 0x03
    i = 0
    while i < len(data):
        if data[i] == IAC and i + 1 < len(data):
            cmd = data[i + 1]
            if cmd in (WILL, WONT, DO, DONT) and i + 2 < len(data):
                opt = data[i + 2]
                if cmd == WILL:
                    replies.extend([IAC, DONT, opt])
                elif cmd == DO:
                    if opt == SGA:
                        replies.extend([IAC, WILL, opt])
                    else:
                        replies.extend([IAC, WONT, opt])
                i += 3
            elif cmd == 0xFA:
                end = data.find(b"\xff\xf0", i + 2)
                i = end + 2 if end != -1 else len(data)
            elif cmd == IAC:
                clean.append(0xFF)
                i += 2
            else:
                i += 2
        else:
            clean.append(data[i])
            i += 1
    return bytes(clean), bytes(replies)


async def bridge_bidirectional(bbs_reader, bbs_writer, mud_reader, mud_writer):
    async def mud_to_bbs():
        try:
            while True:
                data = await mud_reader.read(4096)
                if not data:
                    break
                clean, replies = process_iac_from_server(data)
                if replies:
                    mud_writer.write(replies)
                    await mud_writer.drain()
                if clean:
                    bbs_writer.write(wordwrap_ansi(transliterate_for_bbs(clean)))
                    await bbs_writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            pass
        except Exception as e:
            log.debug(f"mud->bbs forward error: {e}")
        finally:
            try:
                bbs_writer.close()
            except Exception:
                pass

    async def bbs_to_mud():
        line_buf = bytearray()
        try:
            while True:
                data = await bbs_reader.read(4096)
                if not data:
                    break
                for byte in data:
                    if byte in (0x08, 0x7F):
                        if line_buf:
                            line_buf.pop()
                            bbs_writer.write(b"\x08 \x08")
                    elif byte in (0x0D, 0x0A):
                        bbs_writer.write(b"\r\n")
                        mud_writer.write(bytes(line_buf) + b"\r\n")
                        await mud_writer.drain()
                        line_buf.clear()
                    elif 0x20 <= byte <= 0x7E:
                        line_buf.append(byte)
                        bbs_writer.write(bytes([byte]))
                await bbs_writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            pass
        except Exception as e:
            log.debug(f"bbs->mud forward error: {e}")
        finally:
            try:
                mud_writer.close()
            except Exception:
                pass

    await asyncio.gather(bbs_to_mud(), mud_to_bbs(), return_exceptions=True)


async def handle_connection(bbs_reader, bbs_writer, evennia_host, evennia_port):
    peer = bbs_writer.get_extra_info("peername")
    log.info(f"New connection from {peer}")

    # rlogin handshake
    header_buf = b""
    try:
        for _ in range(32):
            chunk = await asyncio.wait_for(bbs_reader.read(256), timeout=5.0)
            if not chunk:
                break
            header_buf += chunk
            if header_buf.count(b"\x00") >= 4:
                break
    except asyncio.TimeoutError:
        log.warning(f"Timeout reading rlogin header from {peer}")
        bbs_writer.close()
        return

    parsed = parse_rlogin_header(header_buf)
    if not parsed:
        log.warning(f"Bad rlogin header from {peer}: {header_buf!r}")
        bbs_writer.close()
        return

    client_user, server_user = parsed
    bbs_username = server_user if server_user else client_user
    log.info(f"rlogin: client={client_user!r} server={server_user!r} -> username={bbs_username!r}")

    bbs_writer.write(b"\x00")
    await bbs_writer.drain()

    # Connect to Evennia
    try:
        mud_reader, mud_writer = await asyncio.wait_for(
            asyncio.open_connection(evennia_host, evennia_port),
            timeout=10.0,
        )
    except Exception as e:
        log.error(f"Cannot connect to Evennia at {evennia_host}:{evennia_port}: {e}")
        bbs_writer.write(b"\r\nHighway Hauler is unavailable. Try again later.\r\n")
        await bbs_writer.drain()
        bbs_writer.close()
        return

    log.info(f"Connected to Evennia at {evennia_host}:{evennia_port}")

    # Automate login
    try:
        await read_until_pattern(mud_reader, "help for more info", timeout=15.0)

        connect_cmd = f"connect {bbs_username} {BRIDGE_PASSWORD}\r\n"
        mud_writer.write(connect_cmd.encode())
        await mud_writer.drain()

        resp_raw, matched = await read_until_any(
            mud_reader, ["You become", "incorrect"], timeout=10.0,
        )

        if matched == "You become":
            log.info(f"Existing account login OK for {bbs_username!r}")
            extra_raw = b""
            try:
                while True:
                    chunk = await asyncio.wait_for(mud_reader.read(4096), timeout=0.5)
                    if not chunk:
                        break
                    extra_raw += chunk
            except asyncio.TimeoutError:
                pass
            full_raw = resp_raw + extra_raw
            clean, replies = process_iac_from_server(full_raw)
            if replies:
                mud_writer.write(replies)
                await mud_writer.drain()
            clean_text = transliterate_for_bbs(clean)
            # Find Highway Hauler banner
            banner_marker = b"Welcome back"
            banner_pos = clean_text.find(banner_marker)
            if banner_pos > 0:
                clean_text = clean_text[banner_pos:]
            bbs_writer.write(b"\x1b[2J\x1b[H" + wordwrap_ansi(clean_text))
            await bbs_writer.drain()
        else:
            log.info(f"Account {bbs_username!r} not found; creating")
            create_cmd = f"create {bbs_username} {BRIDGE_PASSWORD}\r\n"
            mud_writer.write(create_cmd.encode())
            await mud_writer.drain()

            # Evennia may ask [Y]/N? or create immediately with "You can now log"
            create_raw, create_match = await read_until_any(
                mud_reader, ["[Y]/N?", "You can now log"], timeout=10.0,
            )
            if create_match == "[Y]/N?":
                mud_writer.write(b"Y\r\n")
                await mud_writer.drain()
                # After Y, wait for creation to complete
                await read_until_pattern(mud_reader, "You can now log", timeout=10.0)

            # Now connect with the newly created account
            mud_writer.write(connect_cmd.encode())
            await mud_writer.drain()

            login_raw = await read_until_pattern(mud_reader, "You become", timeout=10.0)
            log.info(f"Account created + connected for {bbs_username!r}")
            clean, replies = process_iac_from_server(login_raw)
            if replies:
                mud_writer.write(replies)
                await mud_writer.drain()
            bbs_writer.write(b"\x1b[2J\x1b[H" + transliterate_for_bbs(clean))
            await bbs_writer.drain()

    except (asyncio.TimeoutError, ConnectionError) as e:
        log.error(f"Login automation failed for {bbs_username!r}: {e}")
        bbs_writer.write(b"\r\nLogin failed. Please try again.\r\n")
        await bbs_writer.drain()
        mud_writer.close()
        bbs_writer.close()
        return

    log.info(f"Bridging session for {bbs_username!r}")
    await bridge_bidirectional(bbs_reader, bbs_writer, mud_reader, mud_writer)
    log.info(f"Session ended for {bbs_username!r}")


async def main(listen_port, evennia_port, evennia_host="127.0.0.1"):
    async def handler(reader, writer):
        await handle_connection(reader, writer, evennia_host, evennia_port)

    server = await asyncio.start_server(handler, "0.0.0.0", listen_port)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    log.info(f"rlogin bridge listening on {addrs} -> Evennia {evennia_host}:{evennia_port}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <listen_port> <evennia_port>", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main(int(sys.argv[1]), int(sys.argv[2])))
