# AegisNova OS — Architecture Documentation

## System Architecture Diagram

```mermaid
graph TB
    subgraph "Boot Layer"
        UEFI["🔐 UEFI Secure Boot<br/>+ Kernel Lockdown"]
        GRUB["GRUB2 Bootloader<br/>quiet splash persistence"]
    end

    subgraph "Kernel Layer"
        KERNEL["🐧 Linux 7.0.x-aegisnova"]
        
        subgraph "Security Modules"
            SELINUX["SELinux<br/>(enforcing)"]
            APPARMOR["AppArmor<br/>(profiles)"]
            LOCKDOWN["Lockdown LSM<br/>(integrity)"]
            IMA["IMA/EVM<br/>(measurement)"]
        end

        subgraph "Telemetry"
            EBPF_K["eBPF/XDP<br/>Probes"]
            AUDIT_K["auditd<br/>Syscall Logging"]
            SECCOMP_K["seccomp<br/>Sandbox"]
        end
    end

    subgraph "Userspace"
        subgraph "Red-Team Stack"
            RT_RECON["🔍 Recon<br/>nmap, amass, nuclei"]
            RT_EXPLOIT["💥 Exploitation<br/>metasploit, sqlmap"]
            RT_POST["🔗 Post-Exploit<br/>bloodhound, empire"]
            RT_CRED["🔑 Credentials<br/>hashcat, john"]
            RT_C2["📡 C2<br/>sliver, havoc"]
        end

        subgraph "Blue-Team Stack"
            BT_NET["🌐 Network<br/>suricata, zeek"]
            BT_EDR["🛡️ EDR<br/>wazuh, osquery"]
            BT_SIEM["📊 SIEM<br/>ELK Stack"]
            BT_FORENSIC["🔬 Forensics<br/>volatility, autopsy"]
            BT_HARDEN["🏰 Hardening<br/>lynis, trivy"]
        end

        subgraph "Security Hardening"
            FW["🧱 nftables<br/>Default-Deny"]
            SYSCTL["⚙️ sysctl<br/>30+ params"]
            SSH_H["🔒 SSH<br/>Key-Only"]
            FAP["📋 fapolicyd<br/>Binary Whitelist"]
        end
    end

    subgraph "AI Agent Layer"
        subgraph "Agent 1: LLM-CLI"
            LLAMA["llama.cpp Server<br/>Gemma-2B / GPT-4o"]
            AISHELL["ai-shell CLI<br/>Interactive Queries"]
        end

        subgraph "Agent 2: eBPF Sensor"
            EBPF_S["eBPF Probes<br/>execsnoop, tcpconnect"]
            LANGCHAIN["LangChain Agent<br/>Event Classifier"]
            JOURNAL["systemd-journal<br/>+ Webhook Alerts"]
        end

        subgraph "Agent 3: Red-Team Autopilot"
            AUTOGPT["AutoGPT<br/>Red-Team Plugins"]
            ATOMIC["Atomic Red Team<br/>ATT&CK Tests"]
            MSF_RPC["Metasploit RPC<br/>Exploitation API"]
        end

        subgraph "Agent 4: Blue-Team Analyst"
            JUPYTER["Jupyter Lab<br/>Security Copilot"]
            WAZUH["Wazuh Manager<br/>SIEM Integration"]
            ELK["Elasticsearch<br/>+ Kibana"]
        end
    end

    subgraph "Desktop Layer"
        GNOME["🖥️ GNOME Shell"]
        WHITESUR["WhiteSur Theme<br/>(macOS Look)"]
        DOCK["Dash-to-Dock<br/>(Bottom, Centered)"]
        ICONS["McMojave Icons"]
        FONTS["SF Pro / Menlo"]
        WALL["macOS Wallpapers"]
    end

    %% Connections
    UEFI --> GRUB --> KERNEL
    KERNEL --> SELINUX
    KERNEL --> APPARMOR
    KERNEL --> LOCKDOWN
    KERNEL --> IMA
    KERNEL --> EBPF_K
    KERNEL --> AUDIT_K

    EBPF_K --> EBPF_S
    EBPF_S --> LANGCHAIN
    LANGCHAIN --> LLAMA
    LANGCHAIN --> JOURNAL

    LLAMA --> AISHELL
    LLAMA --> AUTOGPT
    LLAMA --> JUPYTER

    AUTOGPT --> ATOMIC
    AUTOGPT --> MSF_RPC

    JUPYTER --> WAZUH
    JUPYTER --> ELK

    BT_NET --> ELK
    BT_EDR --> ELK
    AUDIT_K --> BT_SIEM

    GNOME --> WHITESUR
    GNOME --> DOCK
    GNOME --> ICONS
```

## Data Flow

```mermaid
sequenceDiagram
    participant K as Kernel (eBPF)
    participant S as eBPF Sensor
    participant L as LLM (llama.cpp)
    participant J as systemd-journal
    participant W as Webhook
    participant E as ELK Stack

    K->>S: Kernel events (exec, open, tcp)
    S->>L: Classify event via prompt
    L->>S: {severity, category, summary}
    
    alt severity >= threshold
        S->>J: Log alert (WARNING)
        S->>W: POST alert JSON
        J->>E: Forward via Filebeat
    else severity < threshold
        S->>J: Log event (DEBUG)
    end
```

## Network Architecture

```mermaid
graph LR
    subgraph "Host Network"
        LO["127.0.0.1<br/>Loopback"]
    end

    subgraph "Docker Networks"
        RT_NET["redteam-net<br/>(bridge)"]
        BT_NET["blueteam-net<br/>(bridge)"]
    end

    subgraph "Exposed Ports (localhost only)"
        P8080["8080 — llama.cpp"]
        P8888["8888 — Jupyter"]
        P9090["9090 — Results UI"]
        P5601["5601 — Kibana"]
        P9200["9200 — Elasticsearch"]
    end

    LO --> P8080
    RT_NET --> P9090
    BT_NET --> P8888
    BT_NET --> P5601
    BT_NET --> P9200
```

## Component Versions

| Component | Version | Source |
|-----------|---------|--------|
| Linux Kernel | 7.0.x | kernel.org |
| Kali Base | Rolling | kali.org |
| llama.cpp | Latest | GitHub |
| Gemma-2B | Q4_K_M | HuggingFace |
| Elasticsearch | 8.13.x | Elastic |
| Wazuh | 4.x | Wazuh |
| WhiteSur Theme | Latest | GitHub (vinceliuice) |
| Docker | CE Latest | Docker |
