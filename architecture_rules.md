architecture_rules.md

Architekturregeln

Minimal-Invasive-Rule
Wenn ein Fehler klar auf Traefik, AdGuard, Authelia oder einen Container begrenzt ist, nur diesen Bereich ändern.
Interface-Rule
Öffentliche Hostnames, Router-Regeln, Ports und Middleware-Zuordnungen werden nicht still geändert.
Dependency-Rule
Keine neuen Container, Resolver, Netzwerke oder Sicherheitskomponenten ohne Begründung.
Separation-Rule
Netzwerkbasis, DNS, Reverse Proxy, Auth und App-Logik bleiben getrennt.
State-Rule
Keine versteckten Zustände durch alte Container, doppelte DHCP-Quellen oder unklare manuelle Hotfixes.
Data-Rule
Konfigurationen bleiben strukturiert und nachvollziehbar. Keine Magie in zufälligen Shell-Skripten.
Change-Size-Rule
Pro Schritt maximal 3 Dateien und nur ein logisch zusammenhängender Patch.
Validation-Rule
Nach jeder Änderung müssen mindestens Syntax, Containerstatus und ein passender Netztest geprüft werden.
Stop-Rule
Sobald ein Basisdienst ausfällt, keine Folgeänderungen an anderen Ebenen.
Report-Rule
Vor jedem Patch kurz nennen: Ziel, Dateien, Risiko, nächster kleinster Schritt.

Verbindliche Arbeitsweise:
Erst Netzbasis prüfen
dann Dienst eingrenzen
dann klein patchen
dann Container und Erreichbarkeit testen
dann dokumentieren

Nicht erlaubt:
DHCP parallel auf Fritzbox und Pi
stille Domain- oder Portänderung
großer Compose-Umbau ohne Einzeltests
Sicherheitsänderungen ohne klare Begründung

Backup-Rule
Backups werden hostgetrennt geplant und ausgeführt. Windows, Pi und VPS sichern ihre eigenen Daten selbst auf das NAS. Das NAS ist Ziel, nicht Orchestrator.
Restore-Rule
Wiederherstellungen erfolgen immer hostbezogen, pfadbezogen und dienstbezogen. Kein globales Blind-Restore.
Host-Role-Rule
Windows-PC ist Haupt-Datenhost. Pi ist Service-Host. NAS ist Backup-/Archivziel. VPS ist Edge-/SaaS-Host.
