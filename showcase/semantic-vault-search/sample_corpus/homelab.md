---
title: Self-hosted infrastructure notes
tags: [infra, network]
---

# Running services at home

I keep a small rack of machines that host my own applications instead of
renting cloud servers. The hypervisor splits each physical box into several
isolated virtual machines, and traffic between them is segmented so a
compromised container cannot reach the rest of the network.

## Network segmentation

Each class of workload sits on its own VLAN. The reverse proxy terminates TLS
and routes requests by hostname. Firewall rules are deny-by-default; only the
ports a service actually needs are opened.

## Backups

Snapshots run nightly to a separate disk pool, and a weekly job copies the
critical volumes off-site. Restores are tested every quarter so the backups are
not merely theoretical.
