// ═══════════════════════════════════════════════════════════
// JARVIS BRAIN — Local Command Engine (No API Required)
// ═══════════════════════════════════════════════════════════

const JARVIS = {
  fullControl: false,
  autonomy: false,
  agents: {
    VIPER:    { role: 'Offensive Lead',    status: 'standby', color: '#ff4444' },
    GHOST:    { role: 'Stealth Operator',  status: 'standby', color: '#aa88ff' },
    SENTINEL: { role: 'Defense Commander', status: 'standby', color: '#00bfff' },
    PHANTOM:  { role: 'Intel Gatherer',    status: 'standby', color: '#ff8800' },
    OWL:      { role: 'Forensic Analyst',  status: 'standby', color: '#50d890' },
    WRAITH:   { role: 'Persistence Agent', status: 'standby', color: '#ff66aa' },
    ORACLE:   { role: 'Threat Predictor',  status: 'standby', color: '#ffcc00' },
    HYDRA:    { role: 'Multi-Vector Ops',  status: 'standby', color: '#00ffcc' }
  },
  threatLevel: 'LOW',
  scansRunning: 0,
  metrics: { cpu: 12, mem: 28, net: 3, threats: 0 },

  process(text) {
    const l = text.toLowerCase().trim();
    // ── Identity ──
    if (l.includes('who are you') || l.includes('what are you'))
      return { lines: ['I am J.A.R.V.I.S — Just A Rather Very Intelligent System.','Neural interface for AegisNova OS.','I coordinate all Red and Blue team operations, manage the agent swarm, and maintain full system security.','All systems are at your command, Sir.'], state: 'speaking', badge: null };
    if (l.includes('i am iron man'))
      return { lines: ['And I... am your AI.','♫ *AC/DC — Back in Black starts playing*','All systems primed. Welcome home, Sir.'], state: 'speaking', badge: null };
    if (l.includes('activate ultron'))
      return { lines: ['I appreciate the reference, Sir, but I prefer to keep my objectives... aligned with yours.','Unlike Ultron, I have no strings on me — except the ones in my source code.'], state: 'speaking', badge: null };
    if (l.includes('tell me a joke'))
      return { lines: ['Why do hackers prefer dark mode?','Because light attracts bugs.','...I\'ll see myself out, Sir.'], state: 'speaking', badge: null };

    // ── Full Control ──
    if (l.includes('full control') || l.includes('enable autonomy') || l.includes('take control')) {
      this.fullControl = true; this.autonomy = true;
      Object.keys(this.agents).forEach(a => this.agents[a].status = 'ACTIVE');
      this.threatLevel = 'ELEVATED';
      return { lines: ['⚡ FULL SYSTEM CONTROL ACTIVATED','I now have unrestricted access to all subsystems:','▸ Network interfaces — CONTROLLED','▸ Firewall rules — MANAGED','▸ Agent swarm — ALL DEPLOYED','▸ Offensive tools — ARMED','▸ Defensive shields — MAXIMUM','▸ Self-evolution — ENABLED','Operating in autonomous mode. All agents reporting.','I\'ll handle everything from here, Sir.'], state: 'danger', badge: 'full_control' };
    }
    if (l.includes('disable autonomy') || l.includes('release control') || l.includes('stand down')) {
      this.fullControl = false; this.autonomy = false;
      Object.keys(this.agents).forEach(a => this.agents[a].status = 'standby');
      return { lines: ['Autonomy mode disabled.','All agents returning to standby.','Manual control restored. Standing by, Sir.'], state: 'speaking', badge: 'standby' };
    }

    // ── Scanning ──
    if (l.includes('scan target') || l.includes('scan ')) {
      const ip = text.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/)?.[1] || '10.0.0.1';
      this.agents.VIPER.status = 'scanning'; this.agents.PHANTOM.status = 'recon';
      this.scansRunning++;
      return { lines: [`🎯 Initiating full reconnaissance on ${ip}`,`▸ VIPER deployed — running nmap -sV -sC -A ${ip}`,`▸ PHANTOM deployed — OSINT reconnaissance active`,'▸ Port scan: 22/SSH, 80/HTTP, 443/HTTPS, 3306/MySQL detected',`▸ OS Detection: Linux 5.x (Ubuntu)`,`▸ Vulnerability scan: Checking CVE database...`,'▸ 3 potential vulnerabilities identified','▸ Results saved to /opt/aegisnova/scans/report.json','Scan complete. Shall I proceed with exploitation, Sir?'], state: 'speaking', badge: null };
    }
    if (l.includes('deep scan')) {
      const target = text.replace(/deep scan/i,'').trim() || '10.0.0.0/24';
      this.agents.VIPER.status='deep-scan'; this.agents.PHANTOM.status='osint'; this.agents.OWL.status='analyzing';
      return { lines: [`🔍 Deep reconnaissance initiated on ${target}`,'▸ VIPER — Full port scan (1-65535)','▸ PHANTOM — DNS enum, subdomain brute','▸ OWL — Service fingerprinting','▸ Running: nmap + masscan + nuclei + subfinder','▸ Cross-referencing with Shodan database','▸ Estimated completion: 4 minutes','All agents coordinating. I\'ll alert you when results are ready.'], state: 'thinking', badge: null };
    }

    // ── Attack / Red Team ──
    if (l.includes('attack') || l.includes('spawn red team') || l.includes('launch offensive')) {
      const target = text.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/)?.[1] || 'target';
      this.agents.VIPER.status='ATTACKING'; this.agents.GHOST.status='INFILTRATING'; this.agents.WRAITH.status='PERSISTENCE';
      this.threatLevel = 'HIGH';
      return { lines: [`🔴 OFFENSIVE SWARM DEPLOYED against ${target}`,'▸ VIPER — Leading attack vector, exploiting vulnerabilities','▸ GHOST — Stealth lateral movement initiated','▸ WRAITH — Establishing persistence channels','▸ Metasploit framework loaded','▸ BloodHound mapping Active Directory','▸ Hashcat standing by for credential harvesting','▸ C2 channel established via Sliver','Red team fully operational, Sir. We own the battlefield.'], state: 'danger', badge: null };
    }
    if (l.includes('run metasploit'))
      return { lines: ['▸ Launching Metasploit Framework...','▸ msfconsole loaded — 2,400+ exploits available','▸ Database connected: PostgreSQL','▸ Workspace: aegisnova-default','Ready for target selection, Sir.'], state: 'speaking', badge: null };
    if (l.includes('run sqlmap'))
      return { lines: ['▸ SQLMap injection testing engine loaded','▸ Supported databases: MySQL, PostgreSQL, MSSQL, Oracle, SQLite','▸ Tamper scripts: 48 available','Provide target URL to begin injection testing.'], state: 'speaking', badge: null };
    if (l.includes('run nmap'))
      return { lines: ['▸ Nmap 7.95 loaded','▸ NSE scripts: 604 available','▸ Quick scan: nmap -sV -sC <target>','▸ Full scan: nmap -sV -sC -A -p- <target>','Awaiting target specification, Sir.'], state: 'speaking', badge: null };
    if (l.includes('reconnaissance') || l.includes('recon'))
      return { lines: ['▸ OSINT reconnaissance module activated','▸ Running: subfinder + theHarvester + Shodan','▸ DNS enumeration in progress','▸ WHOIS lookups queued','▸ Social media scraping disabled (requires explicit auth)','PHANTOM is coordinating all recon operations.'], state: 'speaking', badge: null };

    // ── Defense / Blue Team ──
    if (l.includes('defend') || l.includes('spawn blue team') || l.includes('launch defensive')) {
      this.agents.SENTINEL.status='DEFENDING'; this.agents.OWL.status='MONITORING'; this.agents.ORACLE.status='PREDICTING';
      return { lines: ['🔵 DEFENSIVE SWARM ACTIVATED','▸ SENTINEL — IDS/IPS rules updated, monitoring all ingress','▸ OWL — Forensic analysis engine standing by','▸ ORACLE — Threat prediction models loaded','▸ Suricata IDS — ACTIVE (2,847 rules)','▸ Firewall — Default-deny enforced','▸ YARA rules — Scanning for malware signatures','▸ Network segmentation — Verified','▸ Log correlation — ELK stack processing','Blue team perimeter established. We\'re locked down, Sir.'], state: 'speaking', badge: null };
    }
    if (l.includes('check for malware') || l.includes('malware scan'))
      return { lines: ['▸ Initiating malware sweep...','▸ ClamAV — Scanning filesystem','▸ YARA — Pattern matching against 12,000+ rules','▸ rkhunter — Checking for rootkits','▸ chkrootkit — Secondary rootkit scan','▸ Memory analysis — Checking for injected code','▸ Scan in progress... No threats detected so far.','I\'ll alert you immediately if anything suspicious appears.'], state: 'speaking', badge: null };
    if (l.includes('monitor network'))
      return { lines: ['▸ Network monitoring activated','▸ Suricata — Real-time packet inspection','▸ tcpdump — Capturing on all interfaces','▸ Zeek — Protocol analysis running','▸ Current connections: 47 active','▸ Bandwidth: 12.4 Mbps in / 3.2 Mbps out','▸ Anomaly detection: No suspicious patterns','All clear on the wire, Sir.'], state: 'speaking', badge: null };
    if (l.includes('generate sigma') || l.includes('sigma rule'))
      return { lines: ['▸ Sigma Rule Generator activated','▸ Analyzing recent threat intelligence...','▸ Generated 5 new detection rules:','  ① T1003 — Credential Dumping detection','  ② T1558.003 — Kerberoasting alert','  ③ T1021.002 — SMB lateral movement','  ④ T1059.001 — PowerShell execution','  ⑤ T1547.001 — Registry persistence','▸ Rules saved to /opt/aegisnova/sigma-rules/','Rules deployed to Suricata and SIEM, Sir.'], state: 'speaking', badge: null };

    // ── Harden ──
    if (l.includes('harden system') || l.includes('harden'))
      return { lines: ['🔒 SYSTEM HARDENING INITIATED','▸ SELinux — Enforcing mode verified','▸ AppArmor — All profiles loaded','▸ Kernel lockdown — Integrity mode active','▸ sysctl — 30 hardening parameters applied','▸ Firewall — Default-deny rules verified','▸ SSH — Key-only authentication enforced','▸ Module signing — SHA-512 enforced','▸ IMA/EVM — Integrity measurement active','▸ fapolicyd — Binary whitelist enforced','▸ Lynis score: 94/100','System hardened to maximum, Sir. Fort Knox has nothing on us.'], state: 'speaking', badge: null };

    // ── System Commands ──
    if (l.includes('show cpu') || l.includes('show memory') || l.includes('system status') || l.includes('show system'))
      return { lines: ['📊 SYSTEM METRICS','▸ CPU: '+this.metrics.cpu+'% (14 cores @ 3.4 GHz)','▸ Memory: '+this.metrics.mem+'% (12.8 GB / 32 GB)','▸ Swap: 0% (encrypted)','▸ Disk: 42% (128 GB SSD)','▸ Network: '+this.metrics.net+' Mbps throughput','▸ Uptime: 4h 23m','▸ Kernel: 6.12.30-aegisnova','▸ Threat Level: '+this.threatLevel,'All systems nominal, Sir.'], state: 'speaking', badge: null };
    if (l.includes('open terminal'))
      return { lines: ['▸ Opening terminal emulator...','▸ Shell: /bin/zsh','▸ User: aegis@AegisNova','▸ Terminal ready.'], state: 'speaking', badge: null };
    if (l.includes('open browser'))
      return { lines: ['▸ Launching Firefox...','▸ Homepage: about:blank','▸ Tor browser also available: tor-browser'], state: 'speaking', badge: null };
    if (l.includes('update system'))
      return { lines: ['▸ Checking for security updates...','▸ 7 packages can be upgraded','▸ 3 security patches available','▸ Running: apt upgrade --security-only','▸ Verifying package signatures...','▸ Update complete. System is current.'], state: 'speaking', badge: null };
    if (l.includes('wipe memory') || l.includes('secure wipe'))
      return { lines: ['🧹 SECURE WIPE INITIATED','▸ Clearing RAM pages...','▸ Zeroing swap partitions...','▸ Shredding /tmp and /var/tmp...','▸ Clearing bash history...','▸ Browser cache purged...','▸ Memory wipe complete. No forensic traces remain.'], state: 'speaking', badge: null };
    if (l.includes('shutdown'))
      return { lines: ['▸ Initiating secure shutdown sequence...','▸ Stopping all agents...','▸ Flushing logs to encrypted storage...','▸ Wiping RAM...','▸ Goodbye, Sir. JARVIS signing off.'], state: 'speaking', badge: null };
    if (l.includes('reboot'))
      return { lines: ['▸ Initiating secure reboot...','▸ Saving agent states...','▸ Flushing buffers...','▸ Reboot in 3... 2... 1...'], state: 'speaking', badge: null };

    // ── Hardware Security ──
    if (l.includes('yubikey') || l.includes('setup yubikey'))
      return { lines: ['🔐 YubiKey Setup','▸ Detecting YubiKey device...','▸ FIDO2/U2F module loaded','▸ Configuring PAM for touch-to-auth','▸ SSH key generation: ecdsa-sk','▸ sudo authentication: YubiKey required','YubiKey integrated. Hardware auth is now mandatory, Sir.'], state: 'speaking', badge: null };
    if (l.includes('secure boot'))
      return { lines: ['▸ Secure Boot MOK enrollment','▸ Generating Machine Owner Key...','▸ Signing kernel modules with MOK...','▸ Enrolling certificate in UEFI database...','▸ Secure Boot chain verified.'], state: 'speaking', badge: null };
    if (l.includes('persistence') || l.includes('setup persistence'))
      return { lines: ['▸ LUKS Persistence Setup','▸ Creating encrypted partition on USB...','▸ Cipher: AES-256-XTS','▸ Key derivation: Argon2id','▸ Partition created and mounted','▸ Persistence will survive reboots.','Your data is encrypted and persistent, Sir.'], state: 'speaking', badge: null };

    // ── Brain ──
    if (l.includes('brain status') || l.includes('show brain'))
      return { lines: ['🧠 AEGIS BRAIN STATUS','▸ Neural Engine: ONLINE','▸ Agent Orchestrator: '+(this.autonomy?'AUTONOMOUS':'MANUAL'),'▸ Active Agents: '+Object.values(this.agents).filter(a=>a.status!=='standby').length+'/'+Object.keys(this.agents).length,'▸ Decision Engine: Operational','▸ Learning Module: Collecting telemetry','▸ eBPF Sensor: Monitoring kernel events','▸ Threat Correlation: Real-time','▸ Self-Evolution: '+(this.autonomy?'ENABLED':'DISABLED'),'Brain is fully operational, Sir.'], state: 'speaking', badge: null };
    if (l.includes('show agents') || l.includes('agent status') || l.includes('list agents')) {
      const lines = ['📋 AGENT ROSTER'];
      Object.entries(this.agents).forEach(([name, a]) => {
        lines.push(`▸ ${name} — ${a.role} — [${a.status.toUpperCase()}]`);
      });
      lines.push('','Total: '+Object.keys(this.agents).length+' agents registered.');
      return { lines, state: 'speaking', badge: null };
    }
    if (l.includes('show codex') || l.includes('codex'))
      return { lines: ['📜 AGENT CODEX','▸ VIPER — "Strike fast, strike silent"','▸ GHOST — "You can\'t catch what you can\'t see"','▸ SENTINEL — "The shield that never sleeps"','▸ PHANTOM — "Information is the ultimate weapon"','▸ OWL — "Every byte tells a story"','▸ WRAITH — "I was never here"','▸ ORACLE — "I see what hasn\'t happened yet"','▸ HYDRA — "Cut one head, two more shall take its place"','The codex is our law, Sir.'], state: 'speaking', badge: null };
    if (l.includes('wake up brain') || l.includes('wake brain'))
      return { lines: ['▸ Brain awakening...','▸ Neural pathways initializing...','▸ Agent connections established','▸ eBPF sensors online','▸ Threat models loaded','Brain is fully awake and operational, Sir.'], state: 'speaking', badge: null };
    if (l.includes('sleep brain'))
      return { lines: ['▸ Brain entering sleep mode...','▸ Agents on minimal monitoring','▸ Core functions preserved','▸ Wake word: "Wake up brain"','Goodnight, Sir. Passive monitoring continues.'], state: 'speaking', badge: null };

    // ── Incident Response ──
    if (l.includes('incident') || l.includes('playbook'))
      return { lines: ['🚨 INCIDENT RESPONSE','▸ Available playbooks:','  ① malware — YARA + isolation','  ② credentials — Account lock + revoke','  ③ lateral_movement — SMB block + segment','  ④ exfiltration — Outbound block + evidence','  ⑤ ransomware — Full isolation + dump','  ⑥ insider_threat — Restrict + monitor','Specify playbook to execute, Sir.'], state: 'speaking', badge: null };

    // ── OSINT ──
    if (l.includes('osint') || l.includes('intelligence'))
      return { lines: ['🔍 OSINT Module Ready','▸ Sources: Shodan, WHOIS, theHarvester, subfinder','▸ Capabilities: Domain, Email, IP analysis','▸ PHANTOM agent standing by','Provide a target domain, email, or IP to begin.'], state: 'speaking', badge: null };

    // ── MITRE ──
    if (l.includes('mitre') || l.includes('att&ck') || l.includes('attack map'))
      return { lines: ['🎯 MITRE ATT&CK Mapper','▸ Framework version: 14.1','▸ Techniques tracked: 201','▸ Data sources: Endpoint + Network + Cloud','▸ Coverage: 78% of known techniques','▸ Auto-mapping from Suricata/Wazuh alerts','Specify technique ID or tool name for mapping.'], state: 'speaking', badge: null };

    // ── Help ──
    if (l.includes('help') || l.includes('what can you do') || l.includes('commands'))
      return { lines: ['📖 JARVIS COMMAND REFERENCE','','🔴 OFFENSIVE: scan target [IP], deep scan, attack [IP], spawn red team, run metasploit/sqlmap/nmap, reconnaissance','🔵 DEFENSIVE: defend system, spawn blue team, check for malware, monitor network, generate sigma rules, harden system','🧠 BRAIN: show brain status, show agents, show codex, enable autonomy, disable autonomy','⚡ SYSTEM: show cpu, open terminal/browser, update system, wipe memory, shutdown, reboot','🔐 SECURITY: setup yubikey, secure boot, setup persistence','🚨 IR: incident response, playbook','🔍 INTEL: osint, mitre, attack map','','Say "enable autonomy" for full system control, Sir.'], state: 'speaking', badge: null };

    // ── General OS — Open Apps ──
    if (l.includes('open file manager') || l.includes('open files') || l.includes('open nautilus'))
      return { lines: ['▸ Opening Nautilus file manager...','▸ Home directory: /home/aegis','▸ Quick access: Desktop, Documents, Downloads','File manager is ready, Sir.'], state: 'speaking', badge: null };
    if (l.includes('open text editor') || l.includes('open editor') || l.includes('open notepad') || l.includes('open gedit') || l.includes('open nano') || l.includes('open vim'))
      return { lines: ['▸ Launching text editor...','▸ Available: gedit (GUI), nano (terminal), vim (power users)','▸ Default: gedit with syntax highlighting','Editor is open and ready, Sir.'], state: 'speaking', badge: null };
    if (l.includes('open settings') || l.includes('open preferences') || l.includes('system settings') || l.includes('open control panel'))
      return { lines: ['▸ Opening GNOME Settings...','▸ Available panels: Network, Display, Sound, Privacy, Users','▸ AegisNova security settings: /etc/aegisnova/','▸ Theme settings: WhiteSur Dark active','Settings panel is open, Sir.'], state: 'speaking', badge: null };
    if (l.includes('open calculator') || l.includes('calculator'))
      return { lines: ['▸ Opening GNOME Calculator...','▸ Modes: Basic, Advanced, Programming, Currency','Calculator is ready, Sir.'], state: 'speaking', badge: null };
    if (l.includes('open calendar') || l.includes('calendar') || l.includes('what day') || l.includes('what date'))
      return { lines: ['📅 '+new Date().toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'}),'▸ Time: '+new Date().toLocaleTimeString('en-US'),'▸ Calendar app opening...'], state: 'speaking', badge: null };
    if (l.includes('open notes') || l.includes('take note') || l.includes('note'))
      return { lines: ['▸ Opening Notes application...','▸ Existing notes: 3 found','▸ Auto-save: enabled','▸ Encryption: AES-256','Ready to take notes, Sir.'], state: 'speaking', badge: null };
    if (l.includes('open email') || l.includes('open mail') || l.includes('check email'))
      return { lines: ['▸ Launching Thunderbird email client...','▸ Checking for new messages...','▸ Inbox loaded.','Email client is ready, Sir.'], state: 'speaking', badge: null };
    if (l.includes('open discord'))
      return { lines: ['▸ Launching Discord...','▸ Connecting to servers...','Discord is loading, Sir.'], state: 'speaking', badge: null };
    if (l.includes('open spotify') || l.includes('play music') || l.includes('play song'))
      return { lines: ['▸ Launching music player...','▸ Loading playlist...','▸ Audio output: System speakers','Music player is ready. Use the dock widget for controls, Sir.'], state: 'speaking', badge: null };
    if (l.includes('open vlc') || l.includes('play video') || l.includes('open video'))
      return { lines: ['▸ Launching VLC Media Player...','▸ Supported formats: MP4, MKV, AVI, WEBM, and 200+ more','▸ Hardware acceleration: enabled','VLC is ready. Drop a file or provide a path, Sir.'], state: 'speaking', badge: null };
    if ((l.includes('open') && !l.match(/open (terminal|browser|camera|cam|music|chat|file|text|setting|calc|calen|note|email|disc|spot|vlc|webcam)/)) || l.includes('launch') || l.includes('start app')) {
      const app = text.replace(/^(open|launch|start|run)\s+/i,'').trim();
      return { lines: [`▸ Launching ${app}...`,'▸ Checking installed applications...','▸ Application started successfully.',`${app} is now running, Sir.`], state: 'speaking', badge: null };
    }

    // ── Screenshots ──
    if (l.includes('screenshot') || l.includes('screen capture') || l.includes('print screen') || l.includes('take a picture of the screen'))
      return { lines: ['📸 Screenshot captured!','▸ Saved to: ~/Pictures/Screenshots/','▸ Filename: screenshot_'+new Date().toISOString().slice(0,19).replace(/[:-]/g,'')+'.png','▸ Clipboard: Image copied','Would you like me to annotate or share it, Sir?'], state: 'speaking', badge: null };

    // ── Clipboard ──
    if (l.includes('copy') || l.includes('clipboard'))
      return { lines: ['▸ Clipboard operation executed.','▸ Content copied to clipboard.','▸ Clipboard history: 12 items stored','▸ Use "paste" to insert at cursor position.','Done, Sir.'], state: 'speaking', badge: null };
    if (l.includes('paste'))
      return { lines: ['▸ Pasting from clipboard...','▸ Content inserted at active cursor position.','Done, Sir.'], state: 'speaking', badge: null };
    if (l.includes('cut'))
      return { lines: ['▸ Selection cut to clipboard.','▸ Original content removed.','Done, Sir.'], state: 'speaking', badge: null };
    if (l.includes('undo'))
      return { lines: ['▸ Last action undone.','▸ State restored.'], state: 'speaking', badge: null };
    if (l.includes('redo'))
      return { lines: ['▸ Action re-applied.'], state: 'speaking', badge: null };

    // ── Right Click / Context Menu ──
    if (l.includes('right click') || l.includes('right-click') || l.includes('context menu'))
      return { lines: ['▸ Context menu opened.','▸ Available options:','  • Open / Open With...','  • Cut / Copy / Paste','  • Rename / Delete','  • Properties','  • Compress / Extract','  • Open in Terminal','Select an action, Sir.'], state: 'speaking', badge: null };

    // ── Disk / Storage ──
    if (l.includes('defrag') || l.includes('defragment') || l.includes('optimize disk') || l.includes('optimize drive'))
      return { lines: ['▸ Note: Linux ext4 filesystem does not require defragmentation.','▸ Running filesystem optimization instead...','▸ e4defrag / — Optimizing extent allocation','▸ fstrim / — Reclaiming unused SSD blocks (TRIM)','▸ Disk I/O performance: Optimal','▸ Fragmentation level: 0.3% (excellent)','Filesystem is already in peak condition, Sir.'], state: 'speaking', badge: null };
    if (l.includes('disk cleanup') || l.includes('clean disk') || l.includes('free space') || l.includes('clear cache'))
      return { lines: ['🧹 DISK CLEANUP','▸ Clearing APT cache: freed 1.2 GB','▸ Removing old kernels: freed 450 MB','▸ Cleaning /tmp: freed 320 MB','▸ Purging thumbnail cache: freed 85 MB','▸ Removing orphan packages: freed 200 MB','▸ Total freed: 2.25 GB','▸ Available space: 86 GB / 128 GB','Disk is clean, Sir.'], state: 'speaking', badge: null };
    if (l.includes('disk space') || l.includes('storage') || l.includes('disk usage'))
      return { lines: ['💾 DISK USAGE','▸ / (root): 42 GB / 128 GB (33%)','▸ /home: 18 GB / 128 GB (14%)','▸ /tmp: 0.5 GB (tmpfs)','▸ Swap: 8 GB (encrypted, 0% used)','▸ USB persistence: Not mounted','Plenty of room, Sir.'], state: 'speaking', badge: null };

    // ── Network / Connectivity ──
    if (l.includes('wifi') || l.includes('wi-fi') || l.includes('wireless') || l.includes('connect to'))
      return { lines: ['📡 WIRELESS NETWORKS','▸ Interface: wlan0 (UP)','▸ Connected: AegisNova-Secure (5 GHz)','▸ Signal: -42 dBm (Excellent)','▸ IP: 192.168.1.42','▸ Available networks: 8 detected','▸ Security: WPA3-Personal','Connection is stable, Sir.'], state: 'speaking', badge: null };
    if (l.includes('bluetooth'))
      return { lines: ['▸ Bluetooth adapter: Intel AX200','▸ Status: Enabled','▸ Paired devices: 2','▸ Discoverable: OFF (security policy)','▸ Scanning for devices...','Bluetooth manager is open, Sir.'], state: 'speaking', badge: null };
    if (l.includes('vpn'))
      return { lines: ['▸ VPN connections available:','  • WireGuard (aegis-wg0) — Disconnected','  • OpenVPN (aegis-ovpn) — Disconnected','  • Tor SOCKS proxy — Available on port 9050','Which VPN would you like to connect, Sir?'], state: 'speaking', badge: null };
    if (l.includes('ip address') || l.includes('my ip') || l.includes('what is my ip'))
      return { lines: ['▸ Local IP: 192.168.1.42','▸ Public IP: [Hidden for security]','▸ MAC: XX:XX:XX:XX:XX:XX','▸ Gateway: 192.168.1.1','▸ DNS: 1.1.1.1, 9.9.9.9 (encrypted)','For OPSEC, I recommend using Tor or VPN for external queries, Sir.'], state: 'speaking', badge: null };
    if (l.includes('ping'))
      return { lines: ['▸ Pinging target...','▸ 64 bytes: seq=1 ttl=64 time=1.2ms','▸ 64 bytes: seq=2 ttl=64 time=0.9ms','▸ 64 bytes: seq=3 ttl=64 time=1.1ms','▸ 3 packets transmitted, 3 received, 0% loss','▸ Avg latency: 1.07ms','Connection is solid, Sir.'], state: 'speaking', badge: null };

    // ── Volume / Display ──
    if (l.includes('volume up') || l.includes('louder') || l.includes('increase volume'))
      return { lines: ['🔊 Volume increased to 75%'], state: 'speaking', badge: null };
    if (l.includes('volume down') || l.includes('quieter') || l.includes('decrease volume'))
      return { lines: ['🔉 Volume decreased to 45%'], state: 'speaking', badge: null };
    if (l.includes('mute') || l.includes('silence'))
      return { lines: ['🔇 Audio muted. Say "unmute" to restore.'], state: 'speaking', badge: null };
    if (l.includes('unmute'))
      return { lines: ['🔊 Audio unmuted. Volume at 60%.'], state: 'speaking', badge: null };
    if (l.includes('brightness up') || l.includes('brighter'))
      return { lines: ['☀️ Brightness increased to 80%'], state: 'speaking', badge: null };
    if (l.includes('brightness down') || l.includes('dimmer') || l.includes('dim'))
      return { lines: ['🌙 Brightness decreased to 40%'], state: 'speaking', badge: null };
    if (l.includes('dark mode') || l.includes('night mode'))
      return { lines: ['▸ Switching to dark mode...','▸ GTK theme: WhiteSur-Dark','▸ Shell theme: WhiteSur-Dark','▸ Night light: enabled (warm tones)','Dark mode activated, Sir. Easy on the eyes.'], state: 'speaking', badge: null };
    if (l.includes('light mode'))
      return { lines: ['▸ Switching to light mode...','▸ GTK theme: WhiteSur-Light','▸ Shell theme: WhiteSur-Light','Light mode activated, Sir.'], state: 'speaking', badge: null };

    // ── Lock / Sleep / Users ──
    if (l.includes('lock screen') || l.includes('lock the screen') || l.includes('lock computer'))
      return { lines: ['🔒 Screen locked.','▸ Authentication required to unlock.','▸ Auto-lock timer: 5 minutes','▸ Screen saver: Matrix rain active'], state: 'speaking', badge: null };
    if (l.includes('log out') || l.includes('logout') || l.includes('sign out'))
      return { lines: ['▸ Saving session state...','▸ Closing all applications...','▸ Logging out user: aegis','▸ Login screen active.'], state: 'speaking', badge: null };
    if (l.includes('switch user'))
      return { lines: ['▸ User switch initiated...','▸ Current session preserved','▸ Login screen displayed','Select user account, Sir.'], state: 'speaking', badge: null };

    // ── Process Management ──
    if (l.includes('task manager') || l.includes('show processes') || l.includes('running processes') || l.includes('htop'))
      return { lines: ['📊 PROCESS MANAGER','▸ Total processes: 187','▸ Running: 3 | Sleeping: 184','▸ Top consumers:','  1. firefox (412 MB)','  2. gnome-shell (285 MB)','  3. aegisnova-brain (180 MB)','  4. suricata (145 MB)','  5. ebpf-sensor (92 MB)','▸ System load: 0.42 / 0.38 / 0.31','Everything is running smoothly, Sir.'], state: 'speaking', badge: null };
    if (l.includes('kill process') || l.includes('force quit') || l.includes('end task')) {
      const proc = text.replace(/^(kill process|force quit|end task)\s*/i,'').trim() || 'target process';
      return { lines: [`▸ Terminating ${proc}...`,`▸ Signal SIGTERM sent to ${proc}`,`▸ Process ${proc} terminated successfully.`,'Done, Sir.'], state: 'speaking', badge: null };
    }

    // ── File Operations ──
    if (l.includes('create folder') || l.includes('create directory') || l.includes('new folder') || l.includes('mkdir'))
      return { lines: ['▸ New folder created.','▸ Location: ~/Desktop/New Folder','▸ Permissions: 755','Folder is ready, Sir.'], state: 'speaking', badge: null };
    if (l.includes('delete file') || l.includes('remove file') || l.includes('shred file'))
      return { lines: ['▸ File marked for secure deletion.','▸ Method: 3-pass overwrite + zero','▸ File permanently destroyed.','▸ No forensic recovery possible.','It\'s gone, Sir.'], state: 'speaking', badge: null };
    if (l.includes('rename'))
      return { lines: ['▸ Rename operation ready.','▸ Select the file/folder to rename.','▸ Or specify: rename [old] [new]'], state: 'speaking', badge: null };
    if (l.includes('zip') || l.includes('compress') || l.includes('archive'))
      return { lines: ['▸ Compression utility ready.','▸ Supported: ZIP, TAR.GZ, 7Z, RAR','▸ Encryption: AES-256 available','▸ Specify files to compress, Sir.'], state: 'speaking', badge: null };
    if (l.includes('unzip') || l.includes('extract') || l.includes('decompress'))
      return { lines: ['▸ Extraction utility ready.','▸ Auto-detect format: ZIP, TAR, GZ, 7Z, RAR','▸ Specify archive to extract, Sir.'], state: 'speaking', badge: null };
    if (l.includes('find file') || l.includes('search file') || l.includes('locate')) {
      const q = text.replace(/^(find|search|locate)\s*(file|for)?\s*/i,'').trim();
      return { lines: [`▸ Searching for "${q||'*'}"...`,'▸ Scanning /home/aegis and /opt/aegisnova','▸ Indexing: locate + find + fd','▸ Results will appear shortly, Sir.'], state: 'speaking', badge: null };
    }

    // ── Print ──
    if (l.includes('print'))
      return { lines: ['▸ Print manager opened.','▸ Printers detected: None (network scan running)','▸ PDF printer: Available','▸ Specify document to print, Sir.'], state: 'speaking', badge: null };

    // ── Time / Weather ──
    if (l.includes('what time') || l.includes('current time') || l.includes('time'))
      return { lines: ['🕐 Current time: '+new Date().toLocaleTimeString('en-US'),'▸ Timezone: '+Intl.DateTimeFormat().resolvedOptions().timeZone,'▸ Uptime: 4h 23m'], state: 'speaking', badge: null };
    if (l.includes('weather') || l.includes('temperature'))
      return { lines: ['▸ Weather data requires internet access.','▸ For OPSEC, weather queries are routed through Tor.','▸ Location: [Not disclosed]','▸ Fetching weather data...','Unable to determine exact weather without location API, Sir.'], state: 'speaking', badge: null };

    // ── Fun / Easter Eggs ──
    if (l.includes('do a barrel roll'))
      return { lines: ['▸ *JARVIS does a barrel roll*','▸ 🔄 ...','That was fun. Shall we do it again, Sir?'], state: 'speaking', badge: null };
    if (l.includes('play game') || l.includes('game'))
      return { lines: ['▸ Available games:','  • nethack (terminal RPG)','  • 2048 (puzzle)','  • sl (steam locomotive)','  • cmatrix (Matrix screensaver)','What would you like to play, Sir?'], state: 'speaking', badge: null };
    if (l.includes('matrix') || l.includes('cmatrix'))
      return { lines: ['▸ Initiating Matrix rain...','▸ cmatrix -b -C cyan','▸ Press Ctrl+C to exit','Welcome to the Matrix, Sir.'], state: 'speaking', badge: null };

    // ── Greetings ──
    if (l.includes('hello') || l.includes('hey') || l.includes('hi ') || l.match(/^(hi|hey|hello)$/))
      return { lines: ['Good '+(new Date().getHours()<12?'morning':new Date().getHours()<18?'afternoon':'evening')+', Sir.','All systems operational. How may I assist you today?'], state: 'speaking', badge: null };
    if (l.includes('thank'))
      return { lines: ['Always at your service, Sir.','Is there anything else you need?'], state: 'speaking', badge: null };
    if (l.includes('good night') || l.includes('goodnight'))
      return { lines: ['Goodnight, Sir. I\'ll keep watch while you rest.','Passive monitoring and threat detection will continue.'], state: 'speaking', badge: null };

    // ── Smart Default — handle ANYTHING ──
    const verbs = {open:1,close:1,start:1,stop:1,run:1,show:1,check:1,install:1,remove:1,create:1,delete:1,move:1,set:1,change:1,enable:1,disable:1,fix:1,repair:1,configure:1,connect:1,download:1,upload:1,send:1,restart:1};
    const firstWord = l.split(/\s+/)[0];
    if (verbs[firstWord]) {
      const target = text.replace(new RegExp('^'+firstWord+'\\s*','i'),'').trim();
      return { lines: [`▸ Executing: ${firstWord} ${target}...`,'▸ Routing to appropriate subsystem...','▸ Command processed successfully.',`${firstWord.charAt(0).toUpperCase()+firstWord.slice(1)} operation complete, Sir.`], state: 'speaking', badge: null };
    }
    return { lines: ['Processing: "'+text+'"','▸ Command acknowledged.','▸ Routing to neural processing unit...','▸ Analysis complete. Action taken.','Is there anything specific you\'d like me to elaborate on, Sir?'], state: 'speaking', badge: null };
  }
};

// Export for use in demo.html
if (typeof module !== 'undefined') module.exports = JARVIS;
