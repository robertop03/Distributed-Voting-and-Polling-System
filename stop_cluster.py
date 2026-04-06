import subprocess
from pathlib import Path

OUT_FILE = Path("docker-compose.generated.yml")


def main():
    if not OUT_FILE.exists():
        print(f"{OUT_FILE} not found. Nothing to stop.")
        return

    cmd = ["docker", "compose", "-f", str(OUT_FILE), "down", "-v", "--remove-orphans"]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()