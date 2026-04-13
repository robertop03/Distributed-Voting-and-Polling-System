from pathlib import Path
import subprocess
import sys

OUT_FILE = Path("docker-compose.generated.yml")
NGINX_FILE = Path("nginx.conf")


def build_node_service(node_index: int, total_nodes: int, expose_node_ports: bool = False) -> str:
    node_name = f"node{node_index}"
    port = 8000 + node_index

    peers = []
    for j in range(1, total_nodes + 1):
        if j != node_index:
            peers.append(f"http://node{j}:{8000 + j}")
    peers_str = ",".join(peers)

    ports_block = f'    ports:\n      - "{port}:{port}"\n' if expose_node_ports else ""

    return f"""  {node_name}:
    image: progetto_ds-node:latest
    env_file:
      - .env
    environment:
      - NODE_ID={node_name}
      - PORT={port}
      - PEERS={peers_str}
      - CLUSTER_SIZE={total_nodes}
      - BASE_STARTUP_DELAY=4
      - DATA_DIR=/data
{ports_block}    volumes:
      - {node_name}_data:/data
"""


def build_proxy_service() -> str:
    return """  proxy:
    image: nginx:alpine
    depends_on:
      - node1
    ports:
      - "18080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
"""


def build_compose(total_nodes: int, expose_node_ports: bool = False) -> str:
    node_services = "".join(
        build_node_service(i, total_nodes, expose_node_ports)
        for i in range(1, total_nodes + 1)
    )
    proxy_service = build_proxy_service()
    volumes = "".join(f"  node{i}_data:\n" for i in range(1, total_nodes + 1))

    return f"""services:
{proxy_service}{node_services}
volumes:
{volumes}
"""


def build_nginx_conf(total_nodes: int) -> str:
    locations = []

    for i in range(1, total_nodes + 1):
        container_port = 8000 + i

        locations.append(f"""        location = /node/{i} {{
            return 301 /node/{i}/;
        }}

        location /node/{i}/ {{
            proxy_pass http://node{i}:{container_port}/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
""")

    joined_locations = "\n".join(locations)

    return f"""events {{}}

http {{
    server {{
        listen 80;

        location = / {{
            default_type text/html;
            return 200 "<html><body><h1>Distributed Voting Cluster</h1><p>Open a node UI at <code>/node/1/</code>, <code>/node/2/</code>, ...</p></body></html>";
        }}

{joined_locations}
    }}
}}
"""


def generate_files(total_nodes: int, expose_node_ports: bool = False) -> None:
    OUT_FILE.write_text(build_compose(total_nodes, expose_node_ports), encoding="utf-8")
    NGINX_FILE.write_text(build_nginx_conf(total_nodes), encoding="utf-8")
    print(
        f"Generated {OUT_FILE} and {NGINX_FILE} for {total_nodes} nodes "
        f"(expose_node_ports={expose_node_ports})."
    )


def run_compose() -> None:
    cmd = ["docker", "compose", "-f", str(OUT_FILE), "up", "-d"]
    subprocess.run(cmd, check=True)


def build_node_image() -> None:
    cmd = ["docker", "build", "-t", "progetto_ds-node:latest", "./node"]
    subprocess.run(cmd, check=True)


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python run_cluster.py <num_nodes> [--expose-nodes]")
        sys.exit(1)

    try:
        total_nodes = int(sys.argv[1])
    except ValueError:
        print("Error: <num_nodes> must be an integer.")
        sys.exit(1)

    if total_nodes < 1:
        print("Error: <num_nodes> must be at least 1.")
        sys.exit(1)

    expose_node_ports = False
    if len(sys.argv) == 3:
        if sys.argv[2] != "--expose-nodes":
            print("Error: only supported optional flag is --expose-nodes")
            sys.exit(1)
        expose_node_ports = True

    generate_files(total_nodes, expose_node_ports)
    build_node_image()
    run_compose()


if __name__ == "__main__":
    main()