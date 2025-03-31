import pefile

# Thay đường dẫn file DLL tại đây
dll_path = "C:\\Users\\ACER\\Downloads\\winmm.dll"

pe = pefile.PE(dll_path)

if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
    print(f"{'Ordinal':<10} {'Address':<18} {'Function Name'}")
    print("-" * 50)
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        func_name = exp.name.decode() if exp.name else '(none)'
        print(f"{exp.ordinal:<10} {hex(exp.address):<18} {func_name}")
else:
    print("This DLL has no export table.")
