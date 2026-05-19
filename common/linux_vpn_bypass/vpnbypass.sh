#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Пожалуйста, запустите скрипт через sudo: sudo $0 <название_программы>"
  exit 1
fi

APP_CMD="$1"
if [ -z "$APP_CMD" ]; then
  echo "Использование: sudo $0 <название_программы>"
  exit 1
fi

echo "[*] Автоматический поиск сетевых настроек..."

# 1. Находим активный Wi-Fi интерфейс (начинается на wl)
WIFI_IF=$(ip -br link show | awk '{print $1}' | grep '^wl' | head -n 1)

if [ -z "$WIFI_IF" ]; then
  echo "[-] Ошибка: Активный Wi-Fi интерфейс не найден."
  exit 1
fi
echo "[+] Найден Wi-Fi интерфейс: $WIFI_IF"

# 2. Получаем текущий IP и маску сети (замена устаревшего ifconfig на ip addr)
IP_INFO=$(ip -o -4 addr show dev "$WIFI_IF" | awk '{print $4}')
if [ -z "$IP_INFO" ]; then
  echo "[-] Ошибка: Не удалось получить IP-адрес для интерфейса $WIFI_IF."
  exit 1
fi

CURRENT_IP=$(echo "$IP_INFO" | cut -d/ -f1)
NETMASK=$(echo "$IP_INFO" | cut -d/ -f2)
IP_BASE=$(echo "$CURRENT_IP" | cut -d. -f1-3)

# 3. Получаем IP роутера (шлюз)
GATEWAY=$(ip route show dev "$WIFI_IF" | grep default | awk '{print $3}' | head -n 1)
if [ -z "$GATEWAY" ]; then
  echo "[-] Ошибка: Не удалось определить IP роутера (шлюз)."
  exit 1
fi

# 4. Подбираем свободный IP в подсети для нашего приложения
echo "[*] Ищем свободный IP-адрес в подсети $IP_BASE.0..."
APP_IP=""
for i in {210..245}; do
  TEST_IP="$IP_BASE.$i"
  if [ "$TEST_IP" != "$CURRENT_IP" ] && [ "$TEST_IP" != "$GATEWAY" ]; then
    # Проверяем, свободен ли IP (отправляем 1 пакет с таймаутом 1 сек)
    if ! ping -c 1 -W 1 "$TEST_IP" &>/dev/null; then
      APP_IP="$TEST_IP"
      break
    fi
  fi
done

if [ -z "$APP_IP" ]; then
  echo "[-] Ошибка: Не удалось найти свободный IP-адрес."
  exit 1
fi

echo "[+] Выбран свободный IP для приложения: $APP_IP"
echo "[+] Шлюз роутера: $GATEWAY (Маска: /$NETMASK)"
echo "------------------------------------------------"

NS_NAME="direct_wifi"
CURRENT_USER=$(logname || echo $SUDO_USER)
USER_HOME=$(eval echo ~$CURRENT_USER)

# Разрешаем доступ к X-серверу
xhost +local:netns: &>/dev/null
xhost +SI:localuser:$CURRENT_USER &>/dev/null

echo "[*] Создаем сетевое пространство: $NS_NAME"
ip netns add "$NS_NAME"

echo "[*] Создаем виртуальный ipvlan L2 на базе $WIFI_IF"
ip link add link "$WIFI_IF" name vlan_direct type ipvlan mode l2
ip link set vlan_direct netns "$NS_NAME"

echo "[*] Поднимаем интерфейсы и настраиваем маршрутизацию"
ip netns exec "$NS_NAME" ip link set lo up
ip netns exec "$NS_NAME" ip link set vlan_direct up
ip netns exec "$NS_NAME" ip addr add "$APP_IP/$NETMASK" dev vlan_direct
ip netns exec "$NS_NAME" ip route add default via "$GATEWAY" dev vlan_direct

echo "[*] Настраиваем DNS (Google DNS)"
mkdir -p /etc/netns/$NS_NAME
echo "nameserver 8.8.8.8" > /etc/netns/$NS_NAME/resolv.conf

echo "[*] Запускаем $APP_CMD от имени пользователя $CURRENT_USER..."

# Запуск через su - полностью сбрасывает root-окружение и загружает окружение пользователя
ip netns exec "$NS_NAME" su - "$CURRENT_USER" -c "
  export DISPLAY='$DISPLAY'
  export XAUTHORITY='$XAUTHORITY'
  export WAYLAND_DISPLAY='$WAYLAND_DISPLAY'
  export XDG_RUNTIME_DIR='/run/user/$(id -u $CURRENT_USER)'
  export DBUS_SESSION_BUS_ADDRESS='$DBUS_SESSION_BUS_ADDRESS'
  export HOME='$USER_HOME'

  $APP_CMD
"

# --- Очистка после закрытия ---
echo "[*] Приложение закрыто. Удаляем сетевое пространство..."
ip netns del "$NS_NAME"
rm -rf /etc/netns/$NS_NAME
xhost -local:netns: &>/dev/null
echo "[+] Готово!"