#!/bin/bash
# =====================================================================
#  pymedical restore for Debian / Linux
#  Companion to backup_pymedical.bat (Windows) and to any .sql produced
#  by mariadb-dump.
#
#  Accepts:  .7z  .gz  .zst  or a plain .sql
#
#  Safety design - identical to the Windows version:
#    1. numbered list, you pick
#    2. verify the dump is complete BEFORE touching anything
#    3. pre-restore snapshot of the current database
#    4. type the database name to confirm
#    5. compare table counts afterwards
#
#  Plus three checks that only matter on Linux - see the comments at
#  each step: lower_case_table_names, server max_allowed_packet, and
#  free disk space for the extracted .sql.
#
#  Usage:  sudo ./restore_pymedical.sh --help
# =====================================================================

set -uo pipefail

# ======================= DEFAULTS (overridable) ======================
# Every one of these can be overridden on the command line, so the
# script does not need editing to run against another server, another
# database, or a backup sitting somewhere else.

DB_NAME="pymedical"
BACKUP_DIR="/var/backups/pymedical"

# Leave DB_PASS empty to use Debian's default unix_socket auth for
# root@localhost - that is why this script wants to be run with sudo.
DB_USER="root"
DB_PASS=""
DB_HOST=""            # empty = local socket
DB_PORT=""

# Take a snapshot of the current database before overwriting it.
PRE_SNAPSHOT=1

ASSUME_YES=0
SRC=""
DB_NAME_EXPLICIT=0

# =====================================================================

usage() {
    cat <<EOF
Usage: sudo $(basename "$0") [options] [backup-file]

  -f, --file FILE       backup to restore: .7z .gz .zst or .sql
                        (same as giving it as a bare argument)
  -d, --dir DIR         where to look for backups when no file is given
                        (default: $BACKUP_DIR)
  -n, --database NAME   database to restore into (default: $DB_NAME)
  -u, --user USER       MariaDB user (default: $DB_USER)
  -p, --password PASS   MariaDB password. Omit to use unix_socket auth,
                        which needs sudo. Use --password-file on a
                        shared machine - an argument is visible in ps.
      --password-file F read the password from the first line of F
  -H, --host HOST       connect over TCP to HOST instead of the socket
  -P, --port PORT       port for --host
      --no-snapshot     skip the pre-restore snapshot. Makes the
                        restore irreversible - only for an empty or
                        already-broken database.
  -y, --yes             skip the typed confirmation. For scripted use;
                        it will still refuse a truncated dump.
  -h, --help            this text

Examples:
  sudo $0
  sudo $0 /mnt/usb/pymedical_2026-09-05_0400.7z
  sudo $0 -d /mnt/nas/backup -n pymedical_test
  sudo $0 -f dump.sql -u backup --password-file /root/.dbpass -y
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--file)          SRC="${2:?--file needs a path}"; shift 2 ;;
        -d|--dir)           BACKUP_DIR="${2:?--dir needs a path}"; shift 2 ;;
        -n|--database|--db) DB_NAME="${2:?--database needs a name}"; DB_NAME_EXPLICIT=1; shift 2 ;;
        -u|--user)          DB_USER="${2:?--user needs a name}"; shift 2 ;;
        -p|--password)      DB_PASS="${2:?--password needs a value}"; shift 2 ;;
        --password-file)    DB_PASS=$(head -n1 "${2:?--password-file needs a path}") || exit 1; shift 2 ;;
        -H|--host)          DB_HOST="${2:?--host needs a value}"; shift 2 ;;
        -P|--port)          DB_PORT="${2:?--port needs a value}"; shift 2 ;;
        --no-snapshot)      PRE_SNAPSHOT=0; shift ;;
        -y|--yes)           ASSUME_YES=1; shift ;;
        -h|--help)          usage ;;
        -*)                 echo "Unknown option: $1" >&2; echo "Try --help" >&2; exit 1 ;;
        *)                  SRC="$1"; shift ;;
    esac
done

RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; BLD=$'\e[1m'; RST=$'\e[0m'
[[ -t 1 ]] || { RED=""; GRN=""; YEL=""; BLD=""; RST=""; }

ok()   { echo "${GRN}[OK]${RST}   $*"; }
warn() { echo "${YEL}[WARN]${RST} $*"; }
die()  { echo "${RED}[FAIL]${RST} $*" >&2; exit 1; }

# Portable helpers - stat and numfmt differ between GNU and BSD, and
# this box may not be the only place the script ends up running.
fsize() { wc -c < "$1" | tr -d ' '; }
human() {
    awk -v b="$1" 'BEGIN{
        split("B KB MB GB TB",u," "); i=1
        while (b>=1024 && i<5) { b/=1024; i++ }
        printf (i==1 ? "%d%s\n" : "%.1f%s\n"), b, u[i]
    }'
}
# Table names out of a mariadb-dump file. sed, not grep -P, so this
# also works where grep has no PCRE support.
dump_tables() { sed -n 's/^CREATE TABLE `\([^`]*\)`.*/\1/p' "$1"; }

WORKDIR=""
cleanup() { [[ -n "$WORKDIR" && -d "$WORKDIR" ]] && rm -rf "$WORKDIR"; }
trap cleanup EXIT

echo
echo "${BLD}======================================================${RST}"
echo "${BLD}  pymedical RESTORE  (Debian)${RST}"
echo "${BLD}======================================================${RST}"
echo

# --------------------------------------------------------------
# Step 0 - locate the tools
# On Debian the client is on PATH; mariadb-* is the modern name and
# mysql-* the compatibility symlink, so accept either.
# --------------------------------------------------------------
MYSQL_BIN=$(command -v mariadb || command -v mysql) \
  || die "mariadb client not found. apt install mariadb-client"
DUMP_BIN=$(command -v mariadb-dump || command -v mysqldump) \
  || die "mariadb-dump not found. apt install mariadb-client"

# unix_socket auth only works as the matching system user, and only
# locally - a TCP connection always needs a real password.
if [[ -z "$DB_PASS" && -z "$DB_HOST" && $EUID -ne 0 ]]; then
    die "No password given, so this falls back to unix_socket auth. Run it with sudo,
       or pass -p / --password-file."
fi

CONN=(-u "$DB_USER")
[[ -n "$DB_HOST" ]] && CONN+=(-h "$DB_HOST")
[[ -n "$DB_PORT" ]] && CONN+=(-P "$DB_PORT")

# MYSQL_PWD keeps the password out of the process list - never put it on
# the command line on a multi-user box.
db() {
    if [[ -n "$DB_PASS" ]]; then
        MYSQL_PWD="$DB_PASS" "$MYSQL_BIN" "${CONN[@]}" "$@"
    else
        "$MYSQL_BIN" "${CONN[@]}" "$@"
    fi
}
dbdump() {
    if [[ -n "$DB_PASS" ]]; then
        MYSQL_PWD="$DB_PASS" "$DUMP_BIN" "${CONN[@]}" "$@"
    else
        "$DUMP_BIN" "${CONN[@]}" "$@"
    fi
}
dbq() { db -N -B -e "$1" 2>/dev/null; }

db -e "SELECT 1" >/dev/null 2>&1 \
  || die "Cannot connect to the server as '$DB_USER'${DB_HOST:+ on $DB_HOST}.
       Check that mariadb is running and the credentials are right."


# --------------------------------------------------------------
# Step 1 - choose the backup
# --------------------------------------------------------------
if [[ -n "$SRC" ]]; then
    [[ -f "$SRC" ]] || die "File not found: $SRC"
else
    [[ -d "$BACKUP_DIR" ]] \
      || die "Backup directory does not exist: $BACKUP_DIR
       Point at the right one with  -d DIR , or name a file with  -f FILE ."

    # Any dump is fair game, not just ones named after this database -
    # you often restore a dump copied over from another machine.
    mapfile -t FILES < <(ls -1t "$BACKUP_DIR"/*.7z \
                                "$BACKUP_DIR"/*.sql \
                                "$BACKUP_DIR"/*.sql.gz \
                                "$BACKUP_DIR"/*.sql.zst 2>/dev/null)
    if [[ ${#FILES[@]} -eq 0 ]]; then
        die "No .7z / .sql / .sql.gz / .sql.zst files in $BACKUP_DIR
       Either point at the right directory:   $0 -d /path/to/backups
       or name the file directly:             $0 -f /path/to/dump.7z
       Run  $0 --help  for all options."
    fi

    echo "Available backups in $BACKUP_DIR  -  newest first:"
    echo
    for i in "${!FILES[@]}"; do
        printf "   %2d)  %-45s %10s\n" \
            "$((i+1))" "$(basename "${FILES[$i]}")" \
            "$(du -h "${FILES[$i]}" | cut -f1)"
    done
    echo
    # Never block forever on a prompt nobody can answer - cron, a pipe,
    # an ssh command with no tty.
    [[ -t 0 ]] || die "No backup file given and there is no terminal to ask on.
       Name one explicitly:  $0 -f /path/to/dump.7z"
    read -rp "Which one? Enter a number, or blank to abort: " CHOICE
    [[ -n "$CHOICE" ]] || { echo "Aborted."; exit 1; }
    if ! [[ "$CHOICE" =~ ^[0-9]+$ ]] || (( CHOICE < 1 || CHOICE > ${#FILES[@]} )); then
        die "\"$CHOICE\" is not one of the listed numbers."
    fi
    SRC="${FILES[$((CHOICE-1))]}"
fi

echo
echo "Selected: $SRC"


# --------------------------------------------------------------
# Step 2 - work out the uncompressed size and check we have room
# A half-extracted dump is worse than no dump, so refuse up front
# rather than running /var out of space mid-way.
# --------------------------------------------------------------
SCRATCH_BASE="${TMPDIR:-/var/tmp}"
[[ -d "$SCRATCH_BASE" ]] || SCRATCH_BASE=/tmp
WORKDIR=$(mktemp -d "$SCRATCH_BASE/pymedical_restore.XXXXXX") \
  || die "Could not create a scratch directory under $SCRATCH_BASE"
COMP_SIZE=$(fsize "$SRC")

case "$SRC" in
    *.7z)
        SEVENZIP=$(command -v 7zz || command -v 7z || command -v 7za) \
          || die "Cannot open .7z - install one of:  apt install 7zip   (or p7zip-full)"
        NEED=$("$SEVENZIP" l -slt "$SRC" 2>/dev/null | grep -m1 '^Size = ' | cut -d' ' -f3)
        ;;
    *.gz)  NEED=$(( COMP_SIZE * 6 )) ;;   # estimate
    *.zst) NEED=$(( COMP_SIZE * 6 )) ;;   # estimate
    *.sql) NEED=0 ;;
    *)     die "Unrecognised backup format: $SRC" ;;
esac
NEED=${NEED:-$(( COMP_SIZE * 30 ))}

if (( NEED > 0 )); then
    # df -Pk is the POSIX form and works on GNU and BSD alike.
    # -P and --output are mutually exclusive in GNU coreutils, so do not
    # be tempted back to --output=avail.
    AVAIL=$(df -Pk "$WORKDIR" 2>/dev/null | awk 'NR==2 {print $4 * 1024}')

    if [[ -z "$AVAIL" ]]; then
        warn "Could not read free space for $WORKDIR - skipping the space check."
    else
        printf "Needs about %s of scratch space in %s, %s available.\n" \
            "$(human "$NEED")" "$SCRATCH_BASE" "$(human "$AVAIL")"
        (( AVAIL > NEED + 104857600 )) \
          || die "Not enough free space to extract the dump.
       Free some space, or put the scratch space on a bigger filesystem:
           sudo TMPDIR=/srv/tmp $0 -f \"$SRC\""
    fi
fi


# --------------------------------------------------------------
# Step 3 - verify and extract
# --------------------------------------------------------------
case "$SRC" in
    *.7z)
        echo
        echo "Testing archive integrity..."
        "$SEVENZIP" t "$SRC" >/dev/null \
          || die "Archive is corrupt. Do NOT use it. Try an older backup."
        ok "Archive is intact."
        echo "Extracting..."
        "$SEVENZIP" x "$SRC" -o"$WORKDIR" -y >/dev/null || die "Extraction failed."
        SQL_FILE=$(find "$WORKDIR" -name '*.sql' -type f | head -1)
        ;;
    *.gz)
        echo "Decompressing..."
        gzip -t "$SRC" || die "Archive is corrupt."
        SQL_FILE="$WORKDIR/$(basename "${SRC%.gz}")"
        gzip -dc "$SRC" > "$SQL_FILE" || die "Decompression failed."
        ;;
    *.zst)
        echo "Decompressing..."
        zstd -t "$SRC" || die "Archive is corrupt."
        SQL_FILE="$WORKDIR/$(basename "${SRC%.zst}")"
        zstd -dc "$SRC" > "$SQL_FILE" || die "Decompression failed."
        ;;
    *.sql)
        SQL_FILE="$SRC"
        ;;
esac

[[ -n "${SQL_FILE:-}" && -f "$SQL_FILE" ]] || die "No .sql file found after extraction."

# The trailer is the only reliable proof the dump ran to completion.
tail -c 2000 "$SQL_FILE" | grep -q 'Dump completed' \
  || die "This dump is truncated - no 'Dump completed' trailer. Nothing was changed."

SQL_SIZE=$(fsize "$SQL_FILE")
EXPECT_TABLES=$(dump_tables "$SQL_FILE" | wc -l | tr -d ' ')
ok "Dump is complete: $(human "$SQL_SIZE"), $EXPECT_TABLES tables."


# --------------------------------------------------------------
# Step 3b - whose database is this dump?
#
# A dump taken with --databases carries its own name in
# "CREATE DATABASE `x`" and "USE `x`" lines. Feeding it to the client
# unchanged puts the data in THAT database no matter which one you
# thought you were restoring into. Those two statements are therefore
# stripped at import time and the target is set on the connection.
# --------------------------------------------------------------
mapfile -t DUMP_DBS < <(sed -n 's/^USE `\([^`]*\)`;.*/\1/p' "$SQL_FILE" | sort -u)

if (( ${#DUMP_DBS[@]} > 1 )); then
    die "This dump contains ${#DUMP_DBS[@]} databases (${DUMP_DBS[*]}).
       Restoring several at once into one target is not something this
       script will guess at. Split the dump first."
fi

DUMP_DB="${DUMP_DBS[0]:-}"

# No -n given? Then the dump's own name is the least surprising target.
if [[ -n "$DUMP_DB" && $DB_NAME_EXPLICIT -eq 0 && "$DUMP_DB" != "$DB_NAME" ]]; then
    echo "Dump is from database '$DUMP_DB' and no -n was given - restoring into '$DUMP_DB'."
    DB_NAME="$DUMP_DB"
fi


# --------------------------------------------------------------
# Step 4 - LINUX-ONLY CHECK: table name case
#
# Windows servers run with lower_case_table_names=1: table names are
# folded to lowercase on the way in, so a Windows dump is all lowercase.
# Debian runs with 0: names are case sensitive and stored as written.
#
# Two ways this bites:
#   - a Debian dump containing MixedCase names restored onto Windows
#     silently folds them, and two tables can collide
#   - code that writes `SELECT ... FROM ReturnGoods` works on Windows
#     and fails on Debian if the table came in as returngoods
# --------------------------------------------------------------
SERVER_LCTN=$(dbq "SELECT @@lower_case_table_names")
UPPER_TABLES=$(dump_tables "$SQL_FILE" | grep -c '[A-Z]' || true)

echo "Server lower_case_table_names = $SERVER_LCTN"
if (( UPPER_TABLES > 0 )); then
    warn "$UPPER_TABLES table name(s) in this dump contain uppercase letters:"
    dump_tables "$SQL_FILE" | grep '[A-Z]' | sed 's/^/         /'
    if [[ "$SERVER_LCTN" != "0" ]]; then
        warn "This server folds names to lowercase - they will NOT come back as written,"
        warn "and two names differing only in case would collide."
    else
        warn "They will be restored as written. Make sure the application's SQL"
        warn "uses exactly the same case, or it will get error 1146."
    fi
    echo
fi


# --------------------------------------------------------------
# Step 5 - LINUX-ONLY CHECK: server max_allowed_packet
#
# The dump was written with --max-allowed-packet=1G, so a single
# extended INSERT can be far larger than Debian's stock server limit.
# When it is, the import dies partway with "server has gone away" -
# which looks like a network fault and is not one.
# --------------------------------------------------------------
MAP=$(dbq "SELECT @@global.max_allowed_packet")
if (( MAP < 268435456 )); then
    warn "Server max_allowed_packet is only $(human "$MAP"); raising it to 1G for this restore."
    if db -e "SET GLOBAL max_allowed_packet=1073741824" >/dev/null 2>&1; then
        ok "Raised. This is not persistent - it reverts when mariadb restarts."
        echo "     To make it permanent, add to /etc/mysql/mariadb.conf.d/50-server.cnf:"
        echo "         [mysqld]"
        echo "         max_allowed_packet = 1G"
    else
        warn "Could not raise it - $DB_USER lacks SUPER. If the import dies with"
        warn "\"server has gone away\", this is why. Set it in 50-server.cnf and restart mariadb."
    fi
    echo
fi


# --------------------------------------------------------------
# Step 6 - show what is about to be destroyed
# --------------------------------------------------------------
DB_EXISTS=$(dbq "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$DB_NAME'")
CUR_TABLES=0
[[ "$DB_EXISTS" == "1" ]] && CUR_TABLES=$(dbq \
    "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_TYPE='BASE TABLE'")

echo "------------------------------------------------------"
echo "${BLD} ABOUT TO OVERWRITE THE LIVE DATABASE${RST}"
echo "------------------------------------------------------"
echo "  Target database : $DB_NAME"
if [[ "$DB_EXISTS" == "1" ]]; then
    echo "  Currently holds : $CUR_TABLES tables  -  ${RED}THESE WILL BE DROPPED${RST}"
else
    echo "  Currently       : does not exist, will be created"
fi
echo "  Restoring from  : $(basename "$SRC")"
if [[ -n "$DUMP_DB" && "$DUMP_DB" != "$DB_NAME" ]]; then
    echo "  Dump was from   : ${YEL}$DUMP_DB${RST}  -  will be REDIRECTED into $DB_NAME"
fi
echo "  Will contain    : $EXPECT_TABLES tables"
echo "------------------------------------------------------"
echo
echo "Make sure every pymedical client on the network is closed first."
echo

if (( ASSUME_YES )); then
    echo "--yes given, skipping confirmation."
else
    [[ -t 0 ]] || die "Refusing to overwrite $DB_NAME without confirmation and without a terminal.
       Pass -y / --yes if you really mean to run this unattended."
    read -rp "Type the database name to confirm, anything else aborts: " CONFIRM
    [[ "$CONFIRM" == "$DB_NAME" ]] || { echo "Aborted - nothing was changed."; exit 1; }
fi


# --------------------------------------------------------------
# Step 7 - pre-restore snapshot, so this is undoable
# --------------------------------------------------------------
SNAPSHOT=""
if [[ "$PRE_SNAPSHOT" == "1" && "$DB_EXISTS" == "1" ]]; then
    SNAPSHOT="$BACKUP_DIR/prerestore_${DB_NAME}_$(date +%Y-%m-%d_%H%M%S).sql"
    mkdir -p "$BACKUP_DIR"
    echo
    echo "Taking a pre-restore snapshot of the CURRENT database..."
    DUMP_RC=0
    dbdump --single-transaction --quick \
        --default-character-set=binary --hex-blob --routines --events --triggers \
        --max-allowed-packet=1G --databases "$DB_NAME" --result-file="$SNAPSHOT" || DUMP_RC=$?
    if (( DUMP_RC != 0 )); then
        die "The pre-restore snapshot failed. Refusing to continue - restoring now would be irreversible.
       Set PRE_SNAPSHOT=0 at the top of this file to override."
    fi
    # The snapshot must also be complete, not merely exit 0.
    tail -c 2000 "$SNAPSHOT" | grep -q 'Dump completed' \
      || die "The pre-restore snapshot is truncated. Refusing to continue."
    chmod 600 "$SNAPSHOT"
    ok "Snapshot saved: $SNAPSHOT"
fi


# --------------------------------------------------------------
# Step 8 - drop and restore
# Dropping first is deliberate: a plain import leaves behind any table
# that is no longer in the dump, which is how orphan tables accumulate
# and later throw error 1932.
# --------------------------------------------------------------
echo
echo "Started at $(date '+%H:%M:%S')"
echo "Dropping $DB_NAME..."
db -e "DROP DATABASE IF EXISTS \`$DB_NAME\`" \
  || die "DROP DATABASE failed - see the error above. Usually another client is still
       connected, or $DB_USER lacks the DROP privilege. Nothing was imported."

# Create it here rather than letting the dump do it, so the target name
# is ours. Reuse the dump's own charset/collation clause - these
# databases are not all utf8mb4, some are still latin1 or big5.
CREATE_LINE=$(grep -m1 '^CREATE DATABASE ' "$SQL_FILE" || true)
if [[ -n "$CREATE_LINE" ]]; then
    # swap only the first backticked token, which is the database name
    CREATE_SQL=$(printf '%s' "$CREATE_LINE" | sed "s/\`[^\`]*\`/\`$DB_NAME\`/")
else
    CREATE_SQL="CREATE DATABASE \`$DB_NAME\`;"
fi
db -e "$CREATE_SQL" || die "Could not create database $DB_NAME."

echo "Importing - this takes a few minutes..."
START=$(date +%s)

# The database name is the last argument, so it becomes the connection's
# default. Combined with the sed filter below, every CREATE TABLE lands
# in $DB_NAME regardless of what the dump says.
import() {
    db --default-character-set=binary --max-allowed-packet=1G \
       --init-command="SET unique_checks=0, foreign_key_checks=0" "$DB_NAME"
}
strip_db_stmts() { sed -e '/^CREATE DATABASE /d' -e '/^USE `/d'; }

RC=0
if command -v pv >/dev/null 2>&1; then
    pv "$SQL_FILE" | strip_db_stmts | import
    RC=${PIPESTATUS[2]}
else
    strip_db_stmts < "$SQL_FILE" | import
    RC=${PIPESTATUS[1]}
fi

if [[ $RC -ne 0 ]]; then
    echo
    echo "${RED}[FAIL]${RST} The import reported an error. $DB_NAME is INCOMPLETE."
    echo
    echo "       errno 184 \"Tablespace already exists\" means a stale .ibd file is left"
    echo "       on disk for a table the server no longer knows about. Stop mariadb,"
    echo "       remove the orphan file from /var/lib/mysql/$DB_NAME/, start it again,"
    echo "       then re-run this restore."
    [[ -n "$SNAPSHOT" ]] && echo "       Roll back with:  $MYSQL_BIN -u $DB_USER --default-character-set=binary < \"$SNAPSHOT\""
    exit 1
fi

ELAPSED=$(( $(date +%s) - START ))
echo "Finished at $(date '+%H:%M:%S')  (${ELAPSED}s)"


# --------------------------------------------------------------
# Step 9 - verify the result
# --------------------------------------------------------------
echo
echo "Verifying..."
NEW_TABLES=$(dbq "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_TYPE='BASE TABLE'")
NON_INNODB=$(dbq "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_TYPE='BASE TABLE' AND ENGINE<>'InnoDB'")

echo "  Tables in the dump     : $EXPECT_TABLES"
echo "  Tables in the database : $NEW_TABLES"
echo "  Non-InnoDB tables      : $NON_INNODB"
echo

if [[ "$NEW_TABLES" != "$EXPECT_TABLES" ]]; then
    warn "Table counts do not match. Check the messages above before letting anyone back in."
else
    ok "${BLD}RESTORE COMPLETE.${RST}"
fi
(( NON_INNODB > 0 )) && warn "$NON_INNODB table(s) are not InnoDB - --single-transaction will not cover them in future backups."

if [[ -n "$SNAPSHOT" ]]; then
    echo
    echo "Pre-restore snapshot kept at:"
    echo "  $SNAPSHOT"
    echo "Delete it once you are satisfied the restore is good."
fi
echo

