; Reglas de firewall para el visual remoto (servidor.exe bindea 0.0.0.0:8770/8771).
; Perfil "private" para no exponer en redes públicas. Se agrega al instalar y se
; quita al desinstalar. Si el usuario no es admin, Windows pedirá el prompt normal.

!macro customInstall
  nsExec::Exec 'netsh advfirewall firewall add rule name="LLeD Backend" dir=in action=allow program="$INSTDIR\resources\backend\servidor.exe" enable=yes profile=private'
!macroend

!macro customUnInstall
  nsExec::Exec 'netsh advfirewall firewall delete rule name="LLeD Backend"'
!macroend
