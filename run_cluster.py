import subprocess
import sys
from pathlib import Path

OUT_FILE = Path("docker-compose.generated.yml")


def build_service(node_index: int, total_nodes: int) -> str:
    node_name = f"node{node_index}"
    port = 8000 + node_index

    peers = []
    for j in range(1, total_nodes + 1):
        if j != node_index:
            peers.append(f"http://node{j}:{8000 + j}")
    peers_str = ",".join(peers)

    return f"""  {node_name}:
    build: ./node
    environment:
      - NODE_ID={node_name}
      - PORT={port}
      - PEERS={peers_str}
      - ANTI_ENTROPY_INTERVAL=3
      - CHECKPOINT_INTERVAL=10
      - DATA_DIR=/data
    ports:
      - "{port}:{port}"
    volumes:
      - {node_name}_data:/data
"""


def build_compose(total_nodes: int) -> str:
    services = "".join(build_service(i, total_nodes) for i in range(1, total_nodes + 1))
    volumes = "".join(f"  node{i}_data:\n" for i in range(1, total_nodes + 1))

    return f"""services:
{services}
volumes:
{volumes}
"""


def generate_compose(total_nodes: int) -> None:
    OUT_FILE.write_text(build_compose(total_nodes), encoding="utf-8")
    print(f"Generated {OUT_FILE} for {total_nodes} nodes.")


def run_compose() -> None:
    cmd = ["docker", "compose", "-f", str(OUT_FILE), "up", "--build"]
    subprocess.run(cmd, check=True)


def main():
    if len(sys.argv) != 2:
        print("Usage: python run_cluster.py <num_nodes>")
        sys.exit(1)

    try:
        total_nodes = int(sys.argv[1])
    except ValueError:
        print("Error: <num_nodes> must be an integer.")
        sys.exit(1)

    if total_nodes < 1:
        print("Error: <num_nodes> must be at least 1.")
        sys.exit(1)

    generate_compose(total_nodes)
    run_compose()


if __name__ == "__main__":
    main()