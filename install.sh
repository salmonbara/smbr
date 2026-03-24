#!/bin/bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "[*] Installing smbr..."

chmod +x "$DIR/smbr"

# create arsenal shortcut dynamically
echo '#!/bin/bash
smbr arsenal "$@"' > "$DIR/.s_tmp"

chmod +x "$DIR/.s_tmp"

# decide install location
if [ -w /usr/local/bin ]; then
    BIN_DIR="/usr/local/bin"
else
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
fi

ln -sf "$DIR/smbr" "$BIN_DIR/smbr"
ln -sf "$DIR/.s_tmp" "$BIN_DIR/s"

echo ""
echo "[+] Installed:"
echo "    smbr → main tool"
echo "    s    → shortcut for arsenal"
echo ""
echo "[✓] Done"