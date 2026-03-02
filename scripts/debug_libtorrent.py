"""
Debug: por que o libtorrent não carrega no Windows.

Execute: python scripts/debug_libtorrent.py
(ou, a partir da raiz do projeto: python -m scripts.debug_libtorrent)
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    print("=== Debug: carregamento do libtorrent (usado pelo TorrentP) ===\n")

    # 1. Onde está o Python e site-packages
    print("1. Python:")
    print(f"   executable: {sys.executable}")
    print(f"   version: {sys.version}")
    site_packages = None
    for p in sys.path:
        if "site-packages" in p:
            site_packages = p
            break
    print(f"   site-packages: {site_packages}\n")

    # 2. Pacote libtorrent no disco
    print("2. Pacote libtorrent no disco:")
    try:
        import importlib.util
        spec = importlib.util.find_spec("libtorrent")
        if spec and spec.origin:
            print(f"   origin: {spec.origin}")
            pkg_dir = os.path.dirname(spec.origin)
            if os.path.isdir(pkg_dir):
                for name in sorted(os.listdir(pkg_dir)):
                    print(f"   - {name}")
        else:
            print("   (não encontrado)")
    except Exception as e:
        print(f"   Erro: {e}")
    print()

    # 3. libtorrent-windows-dll (OpenSSL DLLs)
    print("3. Pacote libtorrent-windows-dll (DLLs OpenSSL para Windows):")
    try:
        import libtorrent
        dll_dir = os.path.join(os.path.dirname(libtorrent.__file__), "libtorrent")
        if os.path.isdir(dll_dir):
            for name in sorted(os.listdir(dll_dir)):
                print(f"   - {name}")
        else:
            # libtorrent importou? então não temos __file__ ou a pasta é outra
            print(f"   libtorrent.__file__ = {getattr(libtorrent, '__file__', 'N/A')}")
    except ImportError:
        try:
            import pkg_resources
            dist = pkg_resources.get_distribution("libtorrent-windows-dll")
            print(f"   Instalado: {dist.location}")
        except Exception:
            print("   NÃO instalado. No Windows, instale com:")
            print("   pip install libtorrent-windows-dll")
    print()

    # 4. Tentativa de importar libtorrent
    print("4. Tentativa de importar libtorrent:")
    try:
        import libtorrent as lt
        print("   OK. libtorrent carregou.")
        print(f"   Versão: {getattr(lt, '__version__', '?')}")
    except ImportError as e:
        print(f"   FALHOU: {e}")
        err_msg = str(e).lower()
        if "dll" in err_msg or "módulo" in err_msg or "module" in err_msg:
            print()
            print("   Causa provável: faltam DLLs no Windows.")
            print("   Soluções:")
            print("   A) Instalar DLLs OpenSSL (recomendado):")
            print("      pip install libtorrent-windows-dll")
            print("   B) Instalar Visual C++ Redistributable (x64):")
            print("      https://aka.ms/vs/17/release/vc_redist.x64.exe")
            print("   C) Usar --save-to-watch-folder em vez de --download-direct")
    except Exception as e:
        print(f"   Erro inesperado: {type(e).__name__}: {e}")
    print()

    # 5. Tentativa de importar TorrentP (depende de libtorrent)
    print("5. Tentativa de importar TorrentP:")
    try:
        from torrentp import TorrentDownloader
        print("   OK. TorrentP carregou.")
    except ImportError as e:
        print(f"   FALHOU: {e}")
        if "libtorrent" in str(e):
            print("   (TorrentP falhou porque libtorrent não carregou acima.)")
    print()
    print("=== Fim do debug ===")


if __name__ == "__main__":
    main()
