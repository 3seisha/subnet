import tkinter as tk
from tkinter import messagebox
import ipaddress
import math

# --- バックエンドの計算ロジック ---
def calculate_cidr_from_devices(required_devices, ip_version):
    total_bits = 32 if ip_version == 4 else 128
    if required_devices < 1:
        return None, "必要な機器数は1以上である必要があります。", None
    total_addresses_needed = required_devices + 2
    try:
        host_bits = math.ceil(math.log2(total_addresses_needed))
    except ValueError:
        return None, "必要な機器数に応じたホストビット数の計算に失敗しました。", None
    cidr_prefix = total_bits - host_bits
    if cidr_prefix < 0:
        return None, f"エラー: IPv{ip_version}では機器数が多すぎて、対応できません。", None
    if not (0 <= cidr_prefix <= total_bits):
        return None, f"エラー: CIDRプレフィックスが無効な範囲です。IPv{ip_version}では0から{total_bits}の範囲で指定してください。", None
    if ip_version == 6 and cidr_prefix == 128 and required_devices > 0:
        return None, "エラー: /128は単一ホスト専用です。複数の機器には対応できません。", None
    return cidr_prefix, None, host_bits

def get_network_info_from_cidr(ip_address_str, cidr_prefix):
    try:
        network = ipaddress.ip_network(f"{ip_address_str}/{cidr_prefix}", strict=False)
        version = network.version
        netmask = str(network.netmask) if version == 4 else "N/A (IPv6ではプレフィックス長を使用)"
        broadcast = str(network.broadcast_address) if version == 4 else "N/A (IPv6ではブロードキャストなし)"
        if version == 4:
            available_hosts = str(network.num_addresses - 2)
        else:
            if network.prefixlen == 128:
                available_hosts = "1"
            elif network.prefixlen == 127:
                available_hosts = "2"
            else:
                available_hosts = "膨大"
        host_range = ""
        if version == 4:
            if network.num_addresses - 2 > 0:
                host_range = f"{network.network_address + 1} - {network.broadcast_address - 1}"
            else:
                host_range = "利用可能なIPアドレスがありません。"
        elif version == 6:
            if network.prefixlen == 128:
                host_range = "単一のアドレスです"
            else:
                host_range = f"{network.network_address + 1} から (広大な範囲)"
        info = {
            "version": version,
            "network_address": str(network.network_address),
            "broadcast_address": broadcast,
            "netmask": netmask,
            "available_hosts": available_hosts,
            "host_range": host_range,
            "calculated_prefixlen": network.prefixlen
        }
        return info, None
    except ValueError as e:
        return None, f"エラー: 無効なIPアドレスまたはCIDRプレフィックスです。詳細: {e}"

class SubnetCalculatorApp:
    def __init__(self, master):
        self.master = master
        master.title("サブネット計算ツール (モード切替対応)")
        master.geometry("520x580")
        master.resizable(False, False)

        # モード選択
        self.mode_var = tk.StringVar(value="devices")
        mode_frame = tk.LabelFrame(master, text="モード選択", padx=10, pady=5)
        mode_frame.pack(padx=10, pady=5, fill="x")
        tk.Radiobutton(mode_frame, text="機器数からCIDR算出", variable=self.mode_var, value="devices", command=self.toggle_mode).pack(anchor="w")
        tk.Radiobutton(mode_frame, text="CIDRからホスト数逆算", variable=self.mode_var, value="cidr", command=self.toggle_mode).pack(anchor="w")

        # 入力フォーム
        input_frame = tk.LabelFrame(master, text="入力", padx=10, pady=10)
        input_frame.pack(padx=10, pady=10, fill="x")

        tk.Label(input_frame, text="IPアドレス:").grid(row=0, column=0, sticky="w", pady=5)
        self.ip_entry = tk.Entry(input_frame, width=35)
        self.ip_entry.grid(row=0, column=1, pady=5)
        self.ip_entry.insert(0, "192.168.1.1")

        self.devices_label = tk.Label(input_frame, text="接続したい機器の数:")
        self.devices_label.grid(row=1, column=0, sticky="w", pady=5)
        self.devices_entry = tk.Entry(input_frame, width=35)
        self.devices_entry.grid(row=1, column=1, pady=5)
        self.devices_entry.insert(0, "30")

        self.cidr_label = tk.Label(input_frame, text="CIDR (例: 24, IPv6なら64):")
        self.cidr_entry = tk.Entry(input_frame, width=35)
        self.cidr_entry.insert(0, "24")

        self.calculate_button = tk.Button(master, text="計算する", command=self.calculate)
        self.calculate_button.pack(pady=5)

        self.reset_button = tk.Button(master, text="リセット", command=self.reset_fields)
        self.reset_button.pack(pady=2)

        # 結果表示
        result_frame = tk.LabelFrame(master, text="結果", padx=10, pady=10)
        result_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.results = {}
        keys = ["IPバージョン", "提案されたCIDR", "サブネットマスク", "ネットワークアドレス",
                "ブロードキャストアドレス", "利用可能な機器の数", "IPアドレス範囲"]
        for i, key in enumerate(keys):
            tk.Label(result_frame, text=f"{key}:").grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            self.results[key] = var
            tk.Label(result_frame, textvariable=var, wraplength=400, justify="left").grid(row=i, column=1, sticky="w", pady=2)

        self.toggle_mode()

    def toggle_mode(self):
        mode = self.mode_var.get()
        if mode == "devices":
            self.devices_label.grid(row=1, column=0, sticky="w", pady=5)
            self.devices_entry.grid(row=1, column=1, pady=5)
            self.cidr_label.grid_remove()
            self.cidr_entry.grid_remove()
        else:
            self.devices_label.grid_remove()
            self.devices_entry.grid_remove()
            self.cidr_label.grid(row=1, column=0, sticky="w", pady=5)
            self.cidr_entry.grid(row=1, column=1, pady=5)

    def clear_results(self):
        for key in self.results:
            self.results[key].set("")

    def reset_fields(self):
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, "192.168.1.1")
        self.devices_entry.delete(0, tk.END)
        self.devices_entry.insert(0, "30")
        self.cidr_entry.delete(0, tk.END)
        self.cidr_entry.insert(0, "24")
        self.clear_results()

    def calculate(self):
        self.clear_results()
        ip_str = self.ip_entry.get()
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            version = ip_obj.version
        except ValueError:
            messagebox.showerror("エラー", "IPアドレスが無効です。正しい形式で入力してください。")
            return

        if self.mode_var.get() == "devices":
            try:
                devices = int(self.devices_entry.get())
                if devices <= 0:
                    messagebox.showerror("エラー", "機器数は1以上の整数を入力してください。")
                    return
                cidr, err, host_bits = calculate_cidr_from_devices(devices, version)
                if err:
                    messagebox.showerror("計算エラー", err)
                    return
                info, err = get_network_info_from_cidr(ip_str, cidr)
                if err:
                    messagebox.showerror("ネットワーク情報取得エラー", err)
                    return
                if version == 6:
                    self.results["提案されたCIDR"].set(f"/{cidr} (ホスト部 {host_bits}ビット)")
                else:
                    self.results["提案されたCIDR"].set(f"/{cidr}（{devices}台に最適）")
            except ValueError:
                messagebox.showerror("入力エラー", "機器数には半角数字を入力してください。")
                return
        else:
            try:
                cidr = int(self.cidr_entry.get())
                max_cidr = 32 if version == 4 else 128
                if not (0 <= cidr <= max_cidr):
                    messagebox.showerror("エラー", f"CIDR値が範囲外です。IPv{version}では0から{max_cidr}の範囲で入力してください。")
                    return
                info, err = get_network_info_from_cidr(ip_str, cidr)
                if err:
                    messagebox.showerror("ネットワーク情報取得エラー", err)
                    return
                if version == 4:
                    total_available_hosts = (2 ** (32 - cidr)) - 2
                    self.results["提案されたCIDR"].set(f"/{cidr}（利用可能ホスト数: {total_available_hosts}）")
                else:
                    if cidr == 128:
                        self.results["提案されたCIDR"].set(f"/{cidr}（利用可能ホスト数: 1）")
                    elif cidr == 127:
                        self.results["提案されたCIDR"].set(f"/{cidr}（利用可能ホスト数: 2）")
                    else:
                        self.results["提案されたCIDR"].set(f"/{cidr}（利用可能ホスト数: 膨大）")
            except ValueError:
                messagebox.showerror("入力エラー", "CIDRは半角数字で入力してください。")
                return

        self.results["IPバージョン"].set(f"IPv{info['version']}")
        self.results["サブネットマスク"].set(info["netmask"])
        self.results["ネットワークアドレス"].set(info["network_address"])
        self.results["ブロードキャストアドレス"].set(info["broadcast_address"])
        self.results["利用可能な機器の数"].set(info["available_hosts"])
        self.results["IPアドレス範囲"].set(info["host_range"])

# アプリケーションの実行
if __name__ == "__main__":
    root = tk.Tk()
    app = SubnetCalculatorApp(root)
    root.mainloop()

