current_state.md

Aktueller Stand

Gerade bearbeitet:
Pi-Basisnetz und Rollenabgrenzung zwischen öffentlichem VPS-SaaS und privatem Heimnetz

Letzter stabiler Zustand:
Pi ist als normaler Netzwerkteilnehmer im Heimnetz wieder stabil erreichbar und der VPS trennt öffentliches SaaS unter avataryx.de logisch von privaten Heimnetz-Diensten.

Zuletzt geändert:
Projektklarstellung zur öffentlichen Root-Domain avataryx.de auf dem VPS
Projektklarstellung zur Trennung zwischen öffentlichem SaaS und privaten Heimnetz-Diensten
Pi-Basisnetz lokal auf dem Pi validiert

Was aktuell funktioniert:
Pi hat stabil 192.168.178.10/24 auf eth0
Default-Route zeigt auf 192.168.178.1
Ping zur Fritzbox 192.168.178.1 erfolgreich
Ping zu 8.8.8.8 erfolgreich
Ping zu 1.1.1.1 erfolgreich
DNS-Auflösung über google.com erfolgreich
WireGuard war während des erfolgreichen Pi-Basistests nicht aktiv
AdGuardHome läuft lokal auf dem Pi und lauscht auf Port 53
Docker-Stack auf dem Pi läuft grundsätzlich
avataryx.de ist als öffentliche Root-Domain für die Landingpage des Generators auf dem VPS vorgesehen und logisch von Heimnetz-Diensten getrennt

Was aktuell nicht funktioniert oder noch nicht bestätigt ist:
Es ist noch nicht bestätigt, ob Heimnetz-Clients den Pi aktuell tatsächlich produktiv als DNS-Server verwenden
Die endgültige Zielentscheidung, ob DHCP dauerhaft auf der Fritzbox bleibt oder später wieder bewusst auf den Pi zurückgeht, ist noch nicht verbindlich abgeschlossen
Der WireGuard-Pfad vom VPS ins Heimnetz ist noch nicht als stabiler Produktivpfad validiert
Die externe Erreichbarkeit privater Heimnetz-Dienste über den VPN-Pfad ist noch nicht vollständig geprüft

Bekannte Risiken:
AdGuardHome läuft lokal auf dem Pi, die tatsächliche operative DNS-Rolle im Heimnetz ist aber noch nicht vollständig nachgewiesen
Eine spätere Rückübernahme von DHCP durch den Pi würde wieder eine kritischere Netzrolle bedeuten und braucht klare Recovery-Regeln
Fehlerdiagnose kann erneut kippen, wenn öffentlicher VPS-SaaS-Betrieb und privater Heimnetz-Zugriff vermischt werden
WireGuard-Clients auf Endgeräten können lokale Netztests verfälschen, wenn sie aktiv sind

Beweislage:
Sicher bestätigt:
Pi hat 192.168.178.10/24 auf eth0
Pi hat Default-Route via 192.168.178.1
Ping zur Fritzbox erfolgreich
Ping zu externen IPs erfolgreich
DNS-Auflösung erfolgreich
Port 67 war auf dem Pi nicht als aktiv lauschender DHCP-Dienst sichtbar
WireGuard war beim erfolgreichen Basistest nicht aktiv
avataryx.de ist als öffentliche VPS-Domain für die Generator-Landingpage mit Login und Registrierung festgelegt und gehört nicht zum privaten Heimnetz-Zugriff

Nur vermutet oder noch offen:
Ob Heimnetz-Clients aktuell 192.168.178.10 produktiv als DNS nutzen
Ob der Pi später wieder bewusst DHCP übernehmen soll oder Fritzbox-DHCP dauerhaft Basis bleibt
Ob alle privaten Pi-Dienste nach VPN-Einwahl sauber und konsistent erreichbar sind

Noch ungeprüft:
Produktiver DNS-Pfad der Heimnetz-Clients
Produktiver DNS-Pfad der WireGuard-Clients
Stabiler End-to-End-Zugriff vom VPS-WireGuard ins Heimnetz
Finale externe Erreichbarkeit privater Heimnetz-Dienste ausschließlich über VPN

Nächster geplanter Schritt:
Tatsächliche DNS-Nutzung im Heimnetz prüfen
anschließend WireGuard-Clientpfad zum Pi getrennt validieren
anschließend externe Erreichbarkeit privater Heimnetz-Dienste nur über VPN prüfen

Blocker:
Kein Basisnetz-Blocker mehr auf dem Pi
Offen ist jetzt vor allem die saubere Validierung von DNS-Rolle, WireGuard-Pfad und privatem Fernzugriff

Wichtig für neuen Chat:
Nicht auf dem VPS diagnostizieren, wenn Pi-Basisnetz gemeint ist
Nicht öffentliches SaaS unter avataryx.de mit privaten Heimnetz-Diensten vermischen
avataryx.de ist öffentlich auf dem VPS nur für die Generator-Landingpage mit Login und Registrierung
Heimnetz- und Infrastruktur-Dienste auf dem Pi bleiben privat und sind nicht direkt öffentlich exponiert
Externer Zugriff auf private Heimnetz-Dienste erfolgt nur über VPN
WireGuard-Clients auf Testgeräten vor lokalen Netzdiagnosen bewusst prüfen oder deaktivieren

Kurzstatus:
Der Pi ist als normaler Netzwerkteilnehmer im Heimnetz wieder stabil. Die öffentliche Root-Domain avataryx.de gehört zum SaaS auf dem VPS und ist strikt von privaten Heimnetz-Diensten getrennt. Offene Punkte sind jetzt nicht mehr die Pi-Basis, sondern die tatsächliche DNS-Rolle im Heimnetz, der WireGuard-Pfad und die private externe Erreichbarkeit nur über VPN.


Was fachlich festgezogen ist:
Windows-PC ist Haupt-Datenhost.
Pi ist Infrastruktur- und Service-Host.
NAS ist primäres Backup- und Archivziel.
VPS sichert nur eigene Dienst- und Konfigurationsdaten.
Windows nutzt als Backup-Gruppe 1 X:\, E:\ und C:\Users\d4sd1ng.
Windows nutzt F:\, G:\, Z:\ und Y:\Downloads selektiv.
Pi Backup-Gruppe 1 umfasst die produktiven Host-Pfade von Traefik, Authelia, AdGuard, Vaultwarden, Postgres, Portainer, pgAdmin, Grafana, Prometheus-Konfiguration, Uptime Kuma, Homer sowie Projekt- und Compose-Dateien.
Prometheus-Daten gelten als selektiv.
NAS-Zielstruktur ist fachlich festgelegt als /backup/pi, /backup/windows, /backup/vps sowie /archive/pi, /archive/windows, /archive/vps.
Versionierung ist fachlich festgelegt auf 3 tägliche, 2 wöchentliche und 1 monatlichen Stand.
Backup-Jobs und Restore-Jobs sind fachlich benannt und priorisiert, aber noch nicht implementiert.
