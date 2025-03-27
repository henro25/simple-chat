# Fault-Tolerant Replication Engineering Notebook

This document serves as an engineering notebook entry for re-implementing our chat application backend using gRPC, with fault tolerance achieved via replication, dynamic server discovery, and leader election. It details design decisions, implementation strategies, and addresses replication, primary selection, and two-node fault tolerance.

---

## 1. Overview

### 1.1 Legacy Architecture

- **Client:**  
  A PyQt-based GUI that previously communicated with a single server using raw sockets (via a custom protocol or JSON) and gRPC.

- **Server:**  
  A single node handling client requests and persisting data in a SQLite database.

- **Database:**  
  SQLite stored user accounts and messages.

### 1.2 Goals for the New Architecture

- **Fault Tolerance and Replication:**  
  Implement a primary-backup model where the primary handles all write operations and replicates them to backup servers. In case of primary failure, the remaining nodes synchronize state and elect a new primary.

- **Dynamic Server List Management:**  
  Each server maintains an up-to-date list of active servers. When a new server joins, it contacts a bootstrap server via the **JoinNetwork** RPC to receive the full state (active clients, server list, and database snapshot). The updated state is then broadcast to all nodes via the **UpdateServerList** RPC.

- **Leader Election and Recovery:**  
  A heartbeat mechanism (using the **HealthCheck** RPC) monitors server health. If the primary fails, the backup nodes trigger an election (using a deterministic method based on lowest IP/port) to designate a new primary, which is then announced to clients.

- **Client Resilience:**  
  Clients maintain a local copy of the active server list, perform regular health checks, and automatically reconnect to a functioning server if the primary becomes unreachable.

---

## 2. Detailed Requirements and Fault Tolerance Goals

- **Active Server List:**  
  Every server maintains a persistent or in-memory record of active server endpoints. Any changes are immediately broadcast to all nodes and clients.

- **State Transfer on Joining:**  
  New servers retrieve the full state (active client list and a database snapshot or transaction log) from an existing server upon joining.

- **Primary-Backup Model:**  
  - The primary server processes all write operations (e.g., sending messages, account registrations, deletions) and replicates these operations using dedicated RPCs such as **ReplicateWrite**.  
  - Two-server fault tolerance is ensured by replicating critical operations to at least one backup and by having consistent state transfers on join.

- **Leader Election:**  
  Upon primary failure, the system uses a deterministic algorithm (e.g., selecting the server with the lowest IP/port) to elect a new primary. The new leader synchronizes state and broadcasts its status.

- **Client Failover:**  
  Clients periodically check the primary’s health and, on detecting a failure, automatically switch to another server from the updated server list.

---

## 3. High-Level Design

### 3.1 Dynamic Server Discovery and State Synchronization

- **Join and Update Procedures:**
  - **JoinNetwork RPC:**  
    A new server contacts an existing node to receive the current list of active servers and a state snapshot.
  
  - **UpdateServerList RPC:**  
    Once the joining server updates its local state and adds its endpoint, the updated server list is broadcast to all active nodes and clients.

### 3.2 Primary-Backup Coordination and Replication

- **Write Replication:**  
  The primary server handles client write operations (e.g., **SendMessage**, **DeleteMessage**, **Register**, etc.) and replicates these to backups using the **ReplicateWrite** RPC.  
  Each replication request includes the operation type (e.g., "SEND", "DELETE", "REGISTER") and required data.

- **Health Monitoring:**  
  A dedicated heartbeat thread uses the **HealthCheck** RPC to ensure that all servers are responsive. Missed heartbeats trigger leader election.

- **Leader Election:**  
  In case of primary failure, backup nodes use a deterministic algorithm (sorting by IP/port) to elect a new primary. The election result is then broadcast to ensure all nodes and clients are updated.

### 3.3 Client-Side Resilience

- **Dynamic gRPC Connection Handling:**  
  Clients subscribe to a live update stream that provides the current server list. Before every operation, they perform a health check on the primary.
  
- **Automatic Failover:**  
  On detecting a connection failure, the client uses the updated server list to reconnect to a functioning server with minimal disruption.

---

## 4. Implementation Details

### 4.1 gRPC Protocol Enhancements

The updated `.proto` file now includes:

- **JoinNetwork:**  
  Allows a new server to join the network and retrieve the current server list and state snapshot.

- **UpdateServerList:**  
  Broadcasts changes in the server list to all nodes and clients.

- **HealthCheck:**  
  Used by both servers and clients to verify the status of a node.

- **ReplicateWrite:**  
  Used by the primary to replicate operations (SEND, DELETE, ACK, REGISTER, LOGIN, READ_HISTORY, DELETE_ACCOUNT) to backups.

### 4.2 Server-Side Changes

- **Network Joining:**  
  On startup, if the server is not the first node, it calls **JoinNetwork** on a bootstrap server to receive the current state and server list. It then integrates this state and broadcasts the updated list via **UpdateServerList**.

- **Primary-Backup Management:**  
  - The primary processes all write operations and replicates these using the **ReplicateWrite** RPC.
  - A heartbeat thread (`monitor_servers`) routinely checks the health of all active servers.
  - On detecting a failure, the system triggers the `elect_new_primary` function, which selects a new primary (based on sorting the active servers by IP and port) and broadcasts this change.

- **Edge Case Handling:**
  - **Late Joiners:** Ensure the new server receives a full state snapshot.
  - **Simultaneous Failures:** The heartbeat mechanism and election algorithm are designed to handle multiple node outages.
  - **Delayed Replication:** Synchronous replication for critical operations minimizes state inconsistency.

### 4.3 Client-Side Modifications

- **Local Server List and Health Checks:**  
  Clients keep a copy of the active server list (updated via **PushServerList**) and perform health checks before issuing RPC calls.

- **Automatic Reconnection:**  
  If a client detects the primary is unresponsive, it iterates over the updated server list, testing connectivity, and reconnects to a valid server. While the servers elect a new primary, all actions from the clients are blocked. When a new primary is elected, it will be pushed to the client which then will be redirected to connect to the primary. 

- **State Reconciliation:**  
  Since servers replicate all state changes, clients do not need to perform any additional reconciliation after reconnecting.

### 4.4 Replication and Fault Tolerance Code Highlights

- **Replication Logic:**  
  After a write operation, the primary calls a helper function (`replicate_to_backups`) that iterates over all backup servers (excluding itself) and sends the operation details via **ReplicateWrite**.

- **Ensuring Two-Fault Tolerance:**  
  With replication and state snapshots on join, even if one or two nodes fail, the remaining nodes have an up-to-date state.

- **Leader Election:**  
  The `elect_new_primary` function deterministically selects the node with the lowest IP/port as the new primary and triggers a broadcast update via **UpdateServerList**.

- **gRPC and Networking:**  
  Both the server and client modules include logic to manage multiple gRPC endpoints. Clients automatically switch endpoints if the current primary fails.

---

## 5. Summary

- **Enhanced Protocol Definitions:**  
  New RPCs (JoinNetwork, UpdateServerList, HealthCheck, ReplicateWrite) enable dynamic server management and state replication.

- **Server-Side Enhancements:**  
  - Dynamic server discovery and state synchronization.
  - A primary-backup model with immediate replication of write operations.
  - A heartbeat mechanism to monitor server health and trigger leader election on failure.

- **Client-Side Enhancements:**  
  - Clients maintain an updated server list and perform regular health checks.
  - Automatic reconnection to alternative servers minimizes disruption during primary failures.

- **Fault Tolerance Achievements:**  
  The design ensures that even with the failure of one or two nodes, the system remains resilient. Leader election and state replication guarantee minimal data loss and quick recovery.

---

This document provides a comprehensive and detailed overview of the design, implementation, and key components of our fault-tolerant chat backend. If further clarification or additional details are needed, please feel free to ask.
