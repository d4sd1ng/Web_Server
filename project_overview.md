project_overview.md

Projektname: Server Project

Ziel:
Ein stabiler, modularer Homeserver auf Raspberry Pi Basis mit sauberem Reverse Proxy, interner Namensauflösung, sicherem Zugriff, klaren Zuständigkeiten und kontrollierbarer Docker-Infrastruktur.

Hauptnutzen:
Zentrale Verwaltung interner Dienste
Sicherer Zugriff auf Dienste über definierte Hostnames
Robuste Basis für Homelab, Monitoring, Backup und spätere Erweiterungen

Nicht-Ziel:
Kein ungeplanter Komplettumbau des Netzwerks
Keine spontane Vermischung von Infrastruktur, App-Logik und Experimenten
Keine direkte öffentliche Exposition interner Dienste ohne klaren Sicherheitsweg

Tech-Stack:
Sprache: YAML, Python, Shell
Frameworks: Flask für eigene Apps
Datenhaltung: PostgreSQL, JSON, Dateibasiertes Config-Management
Infrastruktur: Docker, Docker Compose, Traefik, AdGuard Home, Authelia, Nginx, Portainer, WireGuard
Tools: Linux CLI, systemd, journalctl, docker logs, nslookup, curl

Projektstruktur:
/opt/server = Hauptverzeichnis für Infrastruktur und Compose
/opt/server/traefik = Reverse Proxy Konfiguration
/opt/server/nginx = Nginx Konfiguration
/opt/server/traefik/config = Dynamische Traefik-Regeln
/opt/server/monitoring = Monitoring Stack und Konfiguration
app/ oder MyApp = Eigene Flask-Anwendung und Blueprints

Kernmodule:
Traefik = Reverse Proxy, TLS, Router und Service-Zuordnung
Authelia = Zugriffsschutz und Forward Auth
AdGuard Home = DNS im Heimnetz
Fritzbox = Router und idealerweise DHCP-Basis
Docker Compose = Orchestrierung der Container
Flask-App = Eigene Verwaltungs- und Serviceoberflächen

Architekturprinzip:
Klare Trennung von Netzwerkbasis, Reverse Proxy, Auth, DNS und Anwendungslogik
Nur ein DHCP-Server gleichzeitig
Hostnamen und Routing explizit definieren
Interne und externe Domains bewusst trennen
Kleine, überprüfbare Änderungen
Der Hetzner-VPS muss explizit als WireGuard-Server rein.
Pi, Windows-PC und Mobilgeräte müssen explizit als WireGuard-Clients rein.
Die Zugriffstrennung muss fest rein:
dienst.internal.avataryx.de = interner Zugriff im Heimnetz
dienst.avataryx.de = externer Zugriff über VPN
Dazu der klare Satz:
Extern bedeutet hier nicht frei öffentlich aus dem Internet, sondern Zugriff über den VPN-Pfad.

Kritische Invarianten:
Fritzbox bleibt der stabile Basis-Router im Heimnetz
Nur ein aktiver DHCP-Server im Netz
Traefik-Routing darf nicht still durch falsche Netzwerknamen oder Labels brechen
DNS, DHCP und Zugriffsschutz nicht gleichzeitig unkontrolliert umbauen

Wichtige Schnittstellen:
Traefik Router -> Docker Services
Authelia Forward Auth -> geschützte Webdienste
AdGuard DNS -> Heimnetz-Clients
Fritzbox DHCP/Netz -> alle Clients und der Pi
Flask-App -> interne Verwaltungsfunktionen

Tabubereiche:
Kein gleichzeitiger Umbau von DHCP, DNS und Proxy ohne Rollback-Plan
Keine stille Änderung von Domain-Schemata
Keine neuen sicherheitskritischen Dienste ohne klare Zugriffskontrolle
Keine ungeprüften Änderungen an produktiven Compose-Dateien

Kurzbeschreibung für neuen Chat:
Dieses Projekt ist ein modularer Homeserver mit Traefik, Authelia, AdGuard und Docker auf Raspberry Pi Basis. Kritisch sind stabile Netzwerkgrundlagen, genau ein DHCP-Server und saubere Trennung von DNS, Routing und Auth. Vor Änderungen zuerst aktuellen Zustand, letzte Entscheidungen und den Task-Vertrag lesen.






Backup- und Restore-Zielbild:
Windows-PC ist Haupt-Datenhost.
Pi ist Infrastruktur- und Service-Host.
NAS ist primäres Backup- und Archivziel.
VPS sichert nur seine eigenen Dienst- und Konfigurationsdaten.

Windows Backup-Gruppe 1:
X:\
E:\
C:\Users\d4sd1ng

Windows selektiv:
F:\
G:\
Z:\
Y:\Downloads

Pi Backup-Gruppe 1:
/opt/server/docker-compose.yml
/opt/server/project_overview.md
/opt/server/architecture_rules.md
/opt/server/current_state.md
/opt/server/decision_log.md
/opt/server/task_contract.md
/opt/server/traefik/config
/opt/server/traefik/letsencrypt
/opt/server/traefik/traefik.yml
/opt/server/logs/traefik/logs
/opt/server/authelia/config
/opt/server/authelia/redis
/opt/server/adguard/work
/opt/server/adguard/conf
/opt/server/vaultwarden/data
/opt/server/postgres/data
/opt/server/portainer/data
/opt/server/pgadmin/data
/opt/server/monitoring/data/grafana
/opt/server/monitoring/config/prometheus/prometheus.yml
/opt/server/monitoring/data/uptime-kuma
/opt/server/homer/assets

Pi selektiv:
/opt/server/monitoring/data/prometheus

NAS Zielstruktur:
/backup/pi
/backup/windows
/backup/vps
/archive/pi
/archive/windows
/archive/vps

Backup-Jobs:
pi-config-core
pi-services-data
pi-monitoring-optional
win-core-data
win-selective-data
vps-core-config
vps-service-data

Restore-Jobs:
restore-pi-config-core
restore-pi-services-data
restore-pi-monitoring-optional
restore-win-core-data
restore-win-selective-data
restore-vps-core-config
restore-vps-service-data

Versionierung:
3 tägliche
2 wöchentliche
1 monatlicher Stand
