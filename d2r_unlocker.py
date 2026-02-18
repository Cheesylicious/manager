import ctypes
from ctypes import wintypes
import sys
import os

# ------------------------------------------------------------------
# Konfiguration
# ------------------------------------------------------------------
TARGET_PROCESS_NAME = "D2R.exe"
SEARCH_STRING = "check for other instances"

# API Konstanten
SystemExtendedHandleInformation = 64
ObjectNameInformation = 1
PROCESS_DUP_HANDLE = 0x0040
DUPLICATE_CLOSE_SOURCE = 0x00000001
DUPLICATE_SAME_ACCESS = 0x00000002
SE_DEBUG_NAME = "SeDebugPrivilege"
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002

# DLLs laden
ntdll = ctypes.WinDLL('ntdll')
kernel32 = ctypes.WinDLL('kernel32')
advapi32 = ctypes.WinDLL('advapi32')

# ------------------------------------------------------------------
# TYP-DEFINITIONEN (Der Overflow-Fix)
# ------------------------------------------------------------------
# Wir definieren exakt, was rein und raus geht. Das verhindert den Overflow.

LPVOID = ctypes.c_void_p
HANDLE = wintypes.HANDLE
LPHANDLE = ctypes.POINTER(HANDLE)

# DuplicateHandle Definition (Argument 3 war der Übeltäter)
kernel32.DuplicateHandle.argtypes = [
    HANDLE,  # hSourceProcess
    HANDLE,  # hSourceHandle
    HANDLE,  # hTargetProcess (Hier gab es den Crash)
    LPHANDLE,  # lpTargetHandle
    wintypes.DWORD,  # dwDesiredAccess
    wintypes.BOOL,  # bInheritHandle
    wintypes.DWORD  # dwOptions
]
kernel32.DuplicateHandle.restype = wintypes.BOOL

kernel32.GetCurrentProcess.restype = HANDLE
kernel32.CloseHandle.argtypes = [HANDLE]
kernel32.OpenProcess.restype = HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

# Token Stuff
advapi32.OpenProcessToken.argtypes = [HANDLE, wintypes.DWORD, LPHANDLE]
advapi32.OpenProcessToken.restype = wintypes.BOOL


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


advapi32.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wintypes.BOOL


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD),
                ("Privileges", LUID_AND_ATTRIBUTES * 1)]


advapi32.AdjustTokenPrivileges.argtypes = [HANDLE, wintypes.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES), wintypes.DWORD,
                                           LPVOID, LPVOID]
advapi32.AdjustTokenPrivileges.restype = wintypes.BOOL


# ------------------------------------------------------------------
# Strukturen
# ------------------------------------------------------------------
class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(ctypes.Structure):
    _fields_ = [
        ("Object", ctypes.c_void_p),
        ("UniqueProcessId", ctypes.c_size_t),
        ("HandleValue", ctypes.c_size_t),
        ("GrantedAccess", wintypes.ULONG),
        ("CreatorBackTraceIndex", wintypes.USHORT),
        ("ObjectTypeIndex", wintypes.USHORT),
        ("HandleAttributes", wintypes.ULONG),
        ("Reserved", wintypes.ULONG),
    ]


class SYSTEM_HANDLE_INFORMATION_EX(ctypes.Structure):
    _fields_ = [
        ("NumberOfHandles", ctypes.c_size_t),
        ("Reserved", ctypes.c_size_t),
        ("Handles", SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX * 1),
    ]


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.USHORT),
        ("MaximumLength", wintypes.USHORT),
        ("Buffer", ctypes.c_void_p),
    ]


class PUBLIC_OBJECT_NAME_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Name", UNICODE_STRING),
        ("Reserved", wintypes.WCHAR * 1024)
    ]


# ------------------------------------------------------------------
# Logik
# ------------------------------------------------------------------

def enable_debug_privilege():
    h_token = HANDLE()
    luid = LUID()
    tkp = TOKEN_PRIVILEGES()

    # Wir nutzen HANDLE(-1) für den CurrentProcess Pseudo-Handle
    current_proc = HANDLE(-1)

    if not advapi32.OpenProcessToken(current_proc, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(h_token)):
        return False

    if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid)):
        kernel32.CloseHandle(h_token)
        return False

    tkp.PrivilegeCount = 1
    tkp.Privileges[0].Luid = luid
    tkp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED

    if not advapi32.AdjustTokenPrivileges(h_token, False, ctypes.byref(tkp), 0, None, None):
        kernel32.CloseHandle(h_token)
        return False

    kernel32.CloseHandle(h_token)
    return True


def get_d2r_pids():
    pids = []
    try:
        cmd = f'tasklist /FI "IMAGENAME eq {TARGET_PROCESS_NAME}" /FO CSV /NH'
        output = os.popen(cmd).read()
        for line in output.splitlines():
            parts = line.split(',')
            if len(parts) > 1:
                pid_str = parts[1].strip('"')
                if pid_str.isdigit():
                    pids.append(int(pid_str))
    except:
        pass
    return pids


def get_system_handles():
    size = 0x100000
    for i in range(20):
        buf = ctypes.create_string_buffer(size)
        result_len = wintypes.ULONG(0)
        status = ntdll.NtQuerySystemInformation(SystemExtendedHandleInformation, buf, size, ctypes.byref(result_len))
        status = status & 0xffffffff
        if status == 0xC0000004:
            size = result_len.value + 0x10000
            continue
        elif status == 0:
            return buf
        else:
            return None
    return None


def main():
    if ctypes.windll.shell32.IsUserAnAdmin() == 0:
        print("!! ACHTUNG: Keine Admin-Rechte !!")
        return

    print("--- D2R Unlocker v3.0 (64-Bit Fix) ---")
    if enable_debug_privilege():
        print("Debug-Modus: AKTIV")
    else:
        print("Debug-Modus: Inaktiv (Fehler)")

    pids = get_d2r_pids()
    if not pids:
        print(f"Kein {TARGET_PROCESS_NAME} gefunden.")
        return

    # PID in DWORD umwandeln für OpenProcess
    target_pid = pids[0]
    print(f"Ziel-PID: {target_pid}")

    buf = get_system_handles()
    if not buf:
        print("Konnte Handles nicht lesen.")
        return

    sys_info = ctypes.cast(buf, ctypes.POINTER(SYSTEM_HANDLE_INFORMATION_EX))

    try:
        count = sys_info.contents.NumberOfHandles
    except:
        count = 0
    if not isinstance(count, int): count = count.value

    print(f"Pruefe {count} Handles...")

    handle_base = ctypes.addressof(sys_info.contents.Handles)
    stride = ctypes.sizeof(SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX)

    found_matches = 0

    # Wir nutzen HANDLE(-1) für CurrentProcess, das ist sicher
    current_proc_handle = HANDLE(-1)

    for i in range(count):
        entry_ptr = handle_base + (i * stride)
        entry = SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX.from_address(entry_ptr)

        if entry.UniqueProcessId == target_pid:
            # OpenProcess
            h_proc = kernel32.OpenProcess(PROCESS_DUP_HANDLE, False, entry.UniqueProcessId)

            if h_proc:
                dup_h = HANDLE()

                # DuplicateHandle (Jetzt mit definierten Typen!)
                status = kernel32.DuplicateHandle(
                    h_proc,
                    HANDLE(entry.HandleValue),
                    current_proc_handle,  # <--- Hier knallte es vorher
                    ctypes.byref(dup_h),
                    0,
                    False,
                    DUPLICATE_SAME_ACCESS
                )

                if status:
                    name_buf = ctypes.create_string_buffer(4096)
                    if (ntdll.NtQueryObject(dup_h, ObjectNameInformation, name_buf, 4096, None) & 0xffffffff) == 0:
                        name_info = ctypes.cast(name_buf, ctypes.POINTER(PUBLIC_OBJECT_NAME_INFORMATION))
                        if name_info.contents.Name.Buffer and name_info.contents.Name.Length > 0:
                            raw = ctypes.string_at(name_info.contents.Name.Buffer, name_info.contents.Name.Length)
                            try:
                                name_str = raw.decode('utf-16le').lower()
                                if SEARCH_STRING in name_str:
                                    print(f" -> TREFFER: {name_str}")

                                    # Kill
                                    kill_h = HANDLE()
                                    if kernel32.DuplicateHandle(h_proc, HANDLE(entry.HandleValue), current_proc_handle,
                                                                ctypes.byref(kill_h), 0, False, DUPLICATE_CLOSE_SOURCE):
                                        print("    [ERFOLG] Handle geschlossen!")
                                        kernel32.CloseHandle(kill_h)
                                        found_matches += 1
                            except:
                                pass
                    kernel32.CloseHandle(dup_h)
                kernel32.CloseHandle(h_proc)

    if found_matches > 0:
        print(f"\nFertig! {found_matches} Sperre entfernt.")
    else:
        print("\nKein passendes Handle gefunden.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"CRASH: {e}")
        input()