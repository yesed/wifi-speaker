import subprocess
import threading
import re
import time
import json

def monitor_spotifyd():
    DEVICE_REGEX = re.compile(r'EmitSessionClientChangedEvent\("[^"]+", "([^"]+)",')
    TRACK_CHANGED_REGEX = re.compile(r'handling event TrackChanged {.*?name:\s+"([^"]+)".*?covers:.*?url:\s+"([^"]+)".*?artists:.*?name:\s+"([^"]+)".*?album:\s+"([^"]+)"', re.DOTALL)

    process = subprocess.Popen(
        ["spotifyd", "--no-daemon", "--verbose"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    print("Monitoring spotifyd output...")

    global device_name, track_name, artist, album, cover_url, status, active_player

    for line in process.stdout:
        line = line.strip()

        # Device Connected
        if "EmitSessionClientChangedEvent" in line:
            match = DEVICE_REGEX.search(line)
            if match:
                active_player = "sc"
                device_name = match.group(1)
                print(f"Spotifyd Device Connected: {device_name}")

        # Device Disconnected
        elif "EmitSessionDisconnectedEvent" in line:
            print("Spotifyd Device disconnected")
            default_metadata()

        # Track Changed
        elif "handling event TrackChanged" in line:
            match = TRACK_CHANGED_REGEX.search(line)
            if match:
                active_player = "sc"
                track_name = match.group(1)
                cover_url = match.group(2)
                artist = match.group(3)
                album = match.group(4)

        elif "command=Play" in line:
            active_player = "sc"
            status = "playing"

        elif "command=Pause" in line:
            active_player = "sc"
            status = "paused"

def monitor_bluetooth():
    cmds = [
        "power on",
        "agent off",
        "agent NoInputNoOutput",
        "discoverable on",
        "pairable on",
    ]

    process = subprocess.Popen(
        ["bluetoothctl"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    for cmd in cmds:
        print(f"Sending: {cmd}")
        process.stdin.write(cmd + '\n')
        process.stdin.flush()
        time.sleep(0.1)

    print("Bluetoothctl setup complete...")

    bt_device_pair_regex = re.compile(r'Device ([0-9A-F:]{17}) Bonded: yes', re.IGNORECASE)
    bt_track_name_regex = re.compile(r'Title: (.+)', re.IGNORECASE)
    bt_artist_regex = re.compile(r'Artist: (.+)', re.IGNORECASE)

    global device_name, track_name, artist, album, cover_url, status, active_player

    while True:
        output_line = process.stdout.readline()
        if output_line:
            output_line = output_line.strip()
            print(output_line)

            if "Bonded: yes" in output_line:
                match = bt_device_pair_regex.search(output_line)
                if match:
                    device_mac = match.group(1)
                    print(f"Device connected: {device_mac}, trusting it...")

                    process.stdin.write(f"trust {device_mac}\n")
                    process.stdin.flush()

                    device_name = str(process.stdout.readline())
                    device_name = device_name.split(']')[0][1:][7:]

            elif "Connected: yes" in output_line:
                device_name = str(process.stdout.readline())
                device_name = device_name.split(']')[0][1:][7:]
                print("Bluetooth Device Connected: {device_name}")
                active_player = "bt"

            elif "Connected: no" in output_line:
                print("Device Disconnected from Bluetooth")
                default_metadata()

            elif "Title: " in output_line:
                match = bt_track_name_regex.search(output_line)
                if match:
                    active_player = "bt"
                    album = "-"
                    cover_url = None
                    track_name = match.group(1)

            elif "Artist: " in output_line:
                match = bt_artist_regex.search(output_line)
                if match:
                    active_player = "bt"
                    artist = match.group(1)

            elif "Status: " in output_line:
                bt_state = output_line.split("Status: ", 1)[1].strip()
                if bt_state  == "playing":
                    status = "playing"
                elif bt_state  == "paused":
                    status = "paused"
                elif bt_state == "stopped":
                    status = "stopped"


        time.sleep(0.05)

def default_metadata():
    global device_name, track_name, cover_url, artist, album, status, active_player

    device_name = "-"
    track_name = "-"
    cover_url = None
    artist = "-"
    album = "-"
    status = None
    active_player = None

def load_config():
    global config_loaded
    config_loaded = False
    try:
        with open("speaker_config.json", "r") as f:
            return json.load(f)
    except Exception as err:
        print(err)

def main():
    global config_loaded
    config = load_config()
    if config_loaded:
        if config.get("first_boot", True):
            print("First boot detected! Running setup...")
            time.sleep(2)
            subprocess.run(["python3", "speaker_setup.py"])
            #exit()

    t1 = threading.Thread(target=monitor_spotifyd)
    t2 = threading.Thread(target=monitor_bluetooth)
    t1.start()
    t2.start()

    global device_name, track_name, cover_url, artist, album, status, active_player

    default_metadata()

    time.sleep(2)

    while True:
        print(f"\nDevice Name: {device_name}")
        print(f"Track Name: {track_name}")
        print(f"Cover URL: {cover_url}")
        print(f"Artist: {artist}")
        print(f"Album: {album}")
        print(f"Staus: {status}")
        print(f"Active Player: {active_player}")

        time.sleep(5)

if __name__ == "__main__":
    main()
