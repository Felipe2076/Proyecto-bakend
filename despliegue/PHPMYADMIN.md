# phpMyAdmin para SIGED (acceso cerrado)

phpMyAdmin queda **solo en 127.0.0.1:8081 del servidor**. No se abre ningún puerto en AWS: se llega por un túnel SSH.

1. En el servidor, carpeta `/home/ec2-user/siged-docker/docker-deployment`, copiar `phpmyadmin.compose.yaml` y revisar:
   `sudo docker compose -f compose.yaml -f phpmyadmin.compose.yaml config | grep -A3 phpmyadmin`
   (si MySQL está en una red con nombre, agregar esa red al servicio `phpmyadmin`).
2. Encender: `sudo docker compose -f compose.yaml -f phpmyadmin.compose.yaml --profile admin up -d phpmyadmin`
3. Desde el PC, con la clave temporal de EC2 Instance Connect:
   `ssh -i <clave_temporal> -L 8081:127.0.0.1:8081 ec2-user@<IP del servidor>`
4. Abrir `http://127.0.0.1:8081` e ingresar con la cuenta **siged_app** (solo SELECT/INSERT/UPDATE/DELETE: no puede
   borrar tablas ni cambiar la estructura). La cuenta root no se usa en phpMyAdmin.
5. Al terminar, apagarlo (`... stop phpmyadmin`). Todo cambio hecho aquí se refleja al instante en la web y en la API móvil.

Cuidado: phpMyAdmin escribe directo en la base y se salta las validaciones de Django. Úselo para consultar y para
correcciones puntuales; los cambios masivos, por la web o por comandos de `manage.py`.
