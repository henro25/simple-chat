# Fault-Tolerant Replication Engineering Notebook

This document serves as a metadata and engineering notebook entry for re-implementing our chat application backend using gRPC, while adding fault tolerance through replication and persistent storage. It covers design decisions, implementation steps, and answers key questions regarding generated code and network configuration.

---

## 1. Overview

### 1.1 Current Architecture

- **Client:** A PyQt-based GUI that communicates with a single server via raw sockets using a custom wire protocol (or JSON) and gRPC.
- **Server:** A single server handling client requests and persisting data in a SQLite database.  
- **Database:** SQLite is used for persisting user accounts and messages.

### 1.2 Goals for New Architecture

We want to extend our current gRPC-based chat system so that each server maintains a dynamic list of active servers (their IP addresses and ports). When a new server is added (by specifying its server client number and port), it contacts an existing server to obtain the full state—including the active client list and database snapshot. This updated list is then broadcast to all active servers and clients. In addition, if a server goes down, every server and client will update their list to remove that server’s endpoint.

We will use a primary-backup (master-replica) model. The primary server handles client writes and replicates those changes to backups. If the primary goes down, the remaining servers synchronize, elect a new primary, and inform clients so they can switch their gRPC connection.

---

## 2. Requirements and Goals

- Each server maintains a list of active server endpoints (IP/port)
- A new server joining the network contacts an existing server to receive the current server list and the full state (active clients and database snapshot)
- When a server is added, the updated server list is broadcast to all active servers and clients
- If a server goes down, its information is removed from the list and the updated list is broadcast.
- The system follows a primary-backup model: the primary handles all write operations and replicates them to backups.
- If the primary fails, the backups synchronize and elect a new primary.
- Clients maintain their own copy of the server list and automatically switch their gRPC connection to a valid server if the one they are using becomes unreachable.

## 3. High-Level Design

### 3.1 Dynamic Server List & Broadcast:

- Each server stores an in-memory (or small persistent table) list of active servers.
- When a new server joins, it contacts a bootstrap server via a dedicated RPC (e.g., JoinNetwork)
- That server sends the current server list and a state snapshot (which can include the active client list and a pointer to a transaction log or a full DB snapshot).
- The joining server integrates the received state, adds its own info, and then the updated list is broadcast using an UpdateServerList RPC to all servers and clients.
- In case a server fails (detected through heartbeat or timeout mechanisms), the list is updated to remove that server and the change is broadcast.

### 3.2 Primary-Backup Coordination:

- The primary server handles all client write operations (such as sending messages, deleting messages, etc.) and writes these updates to its local SQLite database.
- After each write, the primary sends a replication RPC (for instance, ReplicateWrite for inserts/updates and ReplicateDelete for deletions) to the backup servers.
- Backups update their own persistent store upon receiving replication calls.
- A heartbeat or HealthCheck RPC is used between servers to monitor the primary’s health.
- If the primary fails, the remaining servers run an election algorithm (for example, the server with the lowest IP/port or a preconfigured priority becomes the new primary) and update the state accordingly.
- The new primary is announced via a broadcast so that clients can update their gRPC connection.

### 3.3 Client Behavior:

- Clients maintain a local copy of the active server list, which is updated via broadcasts from servers.
- Before making an RPC call, the client checks the health of the primary server (for example, by using a HealthCheck RPC). If the primary is unresponsive, the client selects an alternative server from its list. 
- When a connection failure occurs, the client retrieves the latest server list (or receives a broadcast update) and re-establishes its gRPC channel with a valid server.
- Clients need no additional reconciliation for state because all servers are synchronized.

## 4. Detailed Implementation

### 4.1 Modifications to the .proto File; add new RPC methods for server list management:

- A **JoinNetwork** RPC, where a new server sends its endpoint and receives the current server list and state snapshot.
- An **UpdateServerList** RPC to broadcast changes in the active server list.
- A **HealthCheck** RPC for both servers and clients, possibly including an indication of which server is the current primary.
- Changes to all original chat service functions to be broadcasted to other active servers when the primary receives a client operation

For example, the .proto file might include messages like:

- **ServerInfo** (with fields for IP and port).
- **ServerListUpdate** (a repeated field of ServerInfo).
- **JoinRequest** and **JoinResponse** (to include the current server list and a state snapshot).
- **HealthCheckRequest** and **HealthCheckResponse**.
- **ReplicationRequest** and **ReplicationResponse**.

### 4.2 Server-Side Changes:

- On startup, a server is the first node if no arguments are provided. If arugments of another server's IP and port number are provided, then it calls **JoinNetwork** on that existing server to receive the current server list and state snapshot.
- The server then updates its local list and adds its own endpoint.
- The updated list is broadcast to all active servers and clients.
- In the primary server’s RPC methods (for example, in SendMessage), after writing to the local SQLite database, the server issues replication RPCs to each backup, which is simply the same client request.
- Implement a heartbeat mechanism using the HealthCheck RPC to monitor the primary’s status.
- On primary failure, the remaining servers perform a simple election (for example, choose the server with the lowest IP/port).
- Once a new primary is elected, all servers synchronize their state if necessary and broadcast the new primary information.

### 4.3 Client-Side Changes:

- Clients are configured with an initial server list, through calling **ServerListUpdate**.
- Clients subscribe to updates for the server list, through a streaming RPC.
- Before each operation, clients perform a lightweight health check on the primary server. If the primary fails, clients select an alternative from the list.
- Client code wraps gRPC calls in error-handling logic; on error, clients re-read the server list and re-establish a connection with a valid server.

### 4.4 Handling Edge Cases:

- New Server Joining Late:
  - Ensure the joining server receives the complete current state (e.g., using a full snapshot or a transaction log) and integrates it properly.
- Simultaneous Primary Failures:
  - Ensure the election algorithm can handle cases where more than one server fails at once (handled from Health Checkups and Lowest IP and port elections)
- Delayed Replication:
  - Accept that a short window of inconsistency might exist and implement retries or synchronous replication for critical operations.
