Task-Name:
Pi-Basisnetz stabilisieren und Folgevalidierung vorbereiten

Ziel:
Den Raspberry Pi wieder als stabilen Netzwerkteilnehmer im Heimnetz bestätigen, die Basischecks abschließen und den nächsten Prüfschritt für DNS-Rolle, WireGuard-Pfad und privaten Fernzugriff sauber abgrenzen.

Status:
Pi-Basisnetz lokal erfolgreich validiert.
Definition of Done des ursprünglichen Basistasks ist erreicht.
Dieser Vertrag beschreibt jetzt den bestätigten Abschluss des Basistasks und die saubere Übergabe an die Folgevalidierung.

Nicht Teil dieser Aufgabe:
Traefik-Refactor
Authelia-Umbau
Öffentliche Exposition privater Heimnetz-Dienste
Neue Container oder neue Netzarchitektur ohne gesonderte Entscheidung
Mischdiagnose zwischen öffentlichem SaaS auf dem VPS und privatem Heimnetz-Zugriff

Betroffene Dateien:
Netplan-Konfiguration
lokale Pi-Netzrolle
Status- und Entscheidungsdokumentation für Folgeprüfungen

Nicht ändern:
Traefik Routing
Authelia Policies
öffentliche Root-Domain avataryx.de für das SaaS auf dem VPS
Container-Architektur außerhalb des Pi-Basisnetzes ohne neue Freigabe

Annahmen:
Fritzbox ist aktuell stabiler Basis-Router
Pi ist lokal per Tastatur und Monitor erreichbar
avataryx.de ist öffentlich auf dem VPS nur für die Landingpage des Generators mit Login und Registrierung
Private Heimnetz-Dienste auf dem Pi bleiben von dieser öffentlichen SaaS-Schicht getrennt
Ein aktiver WireGuard-Client auf einem Testgerät kann lokale Netzdiagnosen verfälschen

Risiken:
DNS-Rolle des Pi im Heimnetz ist noch nicht vollständig verifiziert
Eine spätere Rückübernahme von DHCP durch den Pi würde wieder eine kritischere Netzrolle bedeuten
WireGuard- oder Endgeräte-Routen können Tests auf Heimnetzebene verfälschen
Öffentliches SaaS auf dem VPS und privater Heimnetz-Zugriff dürfen operativ nicht vermischt werden

Definition of Done:
Pi hat stabil 192.168.178.10/24 auf eth0
Pi hat eine funktionierende Default-Route via 192.168.178.1
Pi erreicht 192.168.178.1 erfolgreich
Pi erreicht externes Internet per IP erfolgreich
DNS-Auflösung auf dem Pi funktioniert erfolgreich
Port 67 ist auf dem Pi nicht als aktiver DHCP-Dienst sichtbar
WireGuard war beim erfolgreichen Pi-Basistest nicht aktiv

Bestätigte Checks:
ip a
ip route
ping -c 3 192.168.178.1
ping -c 3 8.8.8.8
ping -c 3 1.1.1.1
ping -c 3 google.com
Prüfung aktiver störender Dienste
Prüfung WireGuard-Status
Prüfung lokaler Resolver-Konfiguration

Folgeaufgabe nach Abschluss dieses Tasks:
Tatsächliche DNS-Nutzung der Heimnetz-Clients prüfen
Produktiven DNS-Pfad der WireGuard-Clients prüfen
WireGuard-Pfad vom VPS ins Heimnetz stabil validieren
Private Heimnetz-Dienste nur über VPN extern prüfen
Zielentscheidung zu DHCP auf Fritzbox oder Pi später getrennt und bewusst treffen

Erlaubte Änderungsgröße:
maximal 3 Dateien
maximal 1 logisch zusammenhängender Patch
keine neue Bibliothek
kein Refactor ohne Freigabe
kein stilles Interface-Ändern

Abbruchbedingungen:
Pi verliert lokale Bedienbarkeit
Basisnetz der Fritzbox bricht erneut weg
unerwartete Interface-Änderung
parallel auftretender Fehler in nicht betroffenem Bereich
öffentliche SaaS-Erreichbarkeit und privater Heimnetz-Zugriff werden in einem Schritt vermischt

Ausgabeformat des Agenten vor dem Patch:
Was wird geändert:
Nur klar abgegrenzter Zielbereich des aktuellen Schritts

Warum nur dort:
Weil Netzbasis, DNS-Rolle, VPN-Pfad und öffentlicher SaaS-Betrieb getrennt geprüft werden müssen

Welche Risiken bestehen:
Dienstkonflikte, falscher Host, aktive WireGuard-Clients, vermischte Rollen zwischen VPS und Heimnetz

Welche Checks laufen danach:
IP, Route, Gateway-Ping, externer Ping, DNS-Test, WireGuard-Status, passende Rollentrennung

Pflicht für den ersten Antwortblock:
Projektziel in einem Satz
betroffene Regeln
betroffene Dateien
kleinster sinnvoller Schritt
noch keine Codeänderung


Aktueller Folgeschritt:
Backup- und Restore-Architektur ist fachlich definiert und als eigener abgeschlossener Planungsblock dokumentiert. Technische Umsetzung der Jobs ist noch offen und gehört in den nächsten Umsetzungsblock.

Fachlich definierte Backup-Jobs:
pi-config-core
pi-services-data
pi-monitoring-optional
win-core-data
win-selective-data
vps-core-config
vps-service-data

Fachlich definierte Restore-Jobs:
restore-pi-config-core
restore-pi-services-data
restore-pi-monitoring-optional
restore-win-core-data
restore-win-selective-data
restore-vps-core-config
restore-vps-service-data
