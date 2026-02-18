## Network Partition Test

To simulate a network partition:

docker network disconnect progetto_ds_default progetto_ds-node3-1
docker network connect ds_isolated progetto_ds-node3-1

Observe divergence.
Reconnect and perform sync to observe convergence.
