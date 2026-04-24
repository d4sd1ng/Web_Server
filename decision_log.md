decision_log.md

Entscheidungslog

Datum: 2026-04-19
Thema: DHCP-Basis im Heimnetz
Status: aktiv
Entscheidung: Fritzbox übernimmt wieder DHCP als Basisdienst.
Warum: Ein exklusiver DHCP-Betrieb auf dem Pi hat das Heimnetz bei Pi-Problemen vollständig blockiert.
Verworfene Alternative: DHCP ausschließlich weiter über den Pi betreiben
Warum verworfen: Single Point of Failure für das gesamte Heimnetz
Eine neue aktive Entscheidung ergänzen:
Interne und externe Hostnames bleiben getrennt.
.internal.avataryx.de ist der interne Namensraum.
.avataryx.de ist der externe Namensraum über VPN.
Diese Trennung ist verbindlich und darf nicht still geändert werden.
Betroffene Dateien oder Module:
Fritzbox Netzwerkeinstellungen
AdGuard/Pi Netzrolle
Folge:
Pi darf nicht erneut ungeprüft zentraler DHCP-Point werden.

Datum: 2026-04-19
Thema: Zugriff auf Fritzbox bei Netzstörung
Status: aktiv
Entscheidung: Notfall-IP 169.254.1.1 wird als Rettungsweg genutzt.
Warum: Normale 192.168.178.1-Erreichbarkeit war zeitweise nicht gegeben.
Verworfene Alternative: Weiter nur über normale Heimnetz-IP arbeiten
Warum verworfen: Nicht robust bei DHCP- und Netzproblemen
Betroffene Dateien oder Module:
keine
Folge:
Bei künftigem Totalausfall erst isolierter Zugriff auf die Fritzbox.

Datum: 2026-04-19
Thema: Fehlerdiagnose
Status: aktiv
Entscheidung: Vor Netzdiagnosen immer Hostidentität prüfen.
Warum: Eine Diagnose lief versehentlich auf dem VPS und nicht auf dem Pi.
Verworfene Alternative: Annahme, dass jede Shell automatisch der Zielhost ist
Warum verworfen: Führt zu falschen Schlüssen und Zeitverlust
Betroffene Dateien oder Module:
Operatives Vorgehen
Folge:
Vor Netztests zuerst Hostname und IP-Kontext prüfen.

Datum: 2026-04-21
Thema: Öffentliche Root-Domain und Trennung zum Heimnetz
Status: aktiv
Entscheidung: avataryx.de bleibt öffentlich auf dem VPS und dient ausschließlich der Landingpage des Generators mit Login und Registrierung.
Warum: Das SaaS-Tool muss öffentlich erreichbar sein, darf aber nicht mit privaten Heimnetz-Diensten oder VPN-Zugängen vermischt werden.
Verworfene Alternative: Die gesamte Domain .avataryx.de pauschal als nur über VPN erreichbaren Bereich behandeln.
Warum verworfen: Die Root-Domain avataryx.de wird bewusst öffentlich für das SaaS-Frontend benötigt, während Heimnetz-Dienste getrennt und privat bleiben müssen.
Betroffene Dateien oder Module:
VPS Routing
öffentliche Domainstrategie
Projektübersicht
Folge:
Öffentliche SaaS-Dienste auf dem VPS und private Heimnetz-Dienste auf dem Pi werden logisch und dokumentarisch strikt getrennt.

Datum: 2026-04-21
Thema: Externer Privat-Zugriff auf Heimdienste
Status: aktiv
Entscheidung: Heimnetz- und Infrastruktur-Dienste auf dem Pi werden nicht direkt öffentlich exponiert. Externer Zugriff darauf erfolgt ausschließlich über den VPN-Pfad.
Warum: Das Heimnetz soll so wenig öffentlich wie möglich sein, während der VPS nur der öffentliche Edge für das SaaS und den WireGuard-Zugang ist.
Verworfene Alternative: Heimdienste unter öffentlichen Hostnames direkt aus dem Internet veröffentlichen.
Warum verworfen: Erhöht unnötig die öffentliche Angriffsfläche des Heimnetzes und vermischt SaaS-Exposition mit privater Infrastruktur.
Betroffene Dateien oder Module:
Pi-Dienste
VPN-Zugriff
interne Hostnames
Folge:
Private Dienste bleiben getrennt von avataryx.de und werden nur intern oder nach VPN-Einwahl erreicht.


Datum: 2026-04-22
Thema: Backup- und Restore-Architektur
Status: aktiv
Entscheidung: Backups werden hostgetrennt organisiert. Windows-PC ist Haupt-Datenhost, Pi ist Service-Host, NAS ist primäres Backup- und Archivziel, VPS sichert nur eigene Dienst- und Konfigurationsdaten. Jeder Host erstellt seine eigenen Backups selbst auf das NAS.
Warum: Reduziert Kopplung, hält Rechte kleiner und passt zur realen Multi-Host-Architektur.
Verworfene Alternative: Zentraler Orchestrator für alle Host-Backups auf Pi oder NAS
Warum verworfen: Erhöht Komplexität, Fremdzugriffe und Fehleranfälligkeit
Betroffene Dateien oder Module:
Backup & Restore
NAS-Rolle
Host-Rollen
Folge:
Backup-Jobs und Restore-Jobs werden hostbezogen definiert.

Datum: 2026-04-22
Thema: Backup-Gruppen und Versionierung
Status: aktiv
Entscheidung: Windows Backup-Gruppe 1 umfasst X:\, E:\ und C:\Users\d4sd1ng. F:\, G:\, Z:\ und Y:\Downloads sind selektiv. Pi Backup-Gruppe 1 umfasst die produktiven Hostpfade der kritischen Dienste und Projektdateien. Versionierung ist 3 tägliche, 2 wöchentliche und 1 monatlicher Stand.
Warum: Trennt kritische Daten von selektiven Massen- oder Komfortdaten und hält Speicherbedarf kontrollierbar.
Verworfene Alternative: Alles pauschal täglich und vollständig sichern
Warum verworfen: Zu hoher Speicherbedarf, zu wenig Priorisierung, unnötige Sicherung reproduzierbarer oder großer Daten
Betroffene Dateien oder Module:
Backup-Gruppen
NAS-Zielstruktur
Restore-Matrix
Folge:
Jobs pi-config-core, pi-services-data, pi-monitoring-optional, win-core-data, win-selective-data, vps-core-config und vps-service-data gelten fachlich als Zielbild.
