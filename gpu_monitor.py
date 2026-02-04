
import time
import sys
from datetime import datetime

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress_bar import ProgressBar
    from rich.text import Text
    import pynvml
except ImportError:
    print("Error: Required libraries are not installed.")
    print("Please run: pip install rich pynvml")
    sys.exit(1)

def get_gpu_data():
    """Fetches and returns a list of dictionaries, each containing data for one GPU."""
    gpu_data = []
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            
            name = pynvml.nvmlDeviceGetName(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            try:
                fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
            except pynvml.NVMLError_NotSupported:
                fan_speed = "N/A" # For GPUs with passive cooling

            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            mem_used = memory_info.used / 1024**2
            mem_total = memory_info.total / 1024**2
            mem_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0

            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_util = utilization.gpu
            
            power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # In Watts
            power_limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000.0 # In Watts
            power_percent = (power_usage / power_limit) * 100 if power_limit > 0 else 0

            gpu_data.append({
                "id": i,
                "name": name,
                "temp": temp,
                "fan_speed": fan_speed,
                "mem_used": mem_used,
                "mem_total": mem_total,
                "mem_percent": mem_percent,
                "gpu_util": gpu_util,
                "power_usage": power_usage,
                "power_limit": power_limit,
                "power_percent": power_percent,
                "driver_version": pynvml.nvmlSystemGetDriverVersion()
            })
    except pynvml.NVMLError as e:
        # Gracefully handle case where NVIDIA drivers might not be running
        return {"error": str(e)}
    finally:
        try:
            pynvml.nvmlShutdown()
        except pynvml.NVMLError:
            pass # Ignore shutdown errors if init failed
    return gpu_data

def generate_table(gpu_data):
    """Generates a rich Table from GPU data."""
    if isinstance(gpu_data, dict) and "error" in gpu_data:
        return Panel(
            Text(f"NVIDIA Driver/SMI Error:\n{gpu_data['error']}", justify="center", style="bold red"),
            title="[bold yellow]GPU Monitor[/bold yellow]",
            border_style="red"
        )

    table = Table(title="[bold yellow]GPU Monitor[/bold yellow]", expand=True, border_style="green")
    
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("GPU Name", style="magenta")
    table.add_column("Temp", justify="right", style="bright_green")
    table.add_column("Fan", justify="right", style="green")
    table.add_column("Power (W)", justify="center", style="yellow")
    table.add_column("Memory (MiB)", justify="center", style="blue")
    table.add_column("GPU Util", justify="center", style="purple")

    for gpu in gpu_data:
        # Temperature color
        if gpu['temp'] >= 80:
            temp_style = "bold red"
        elif gpu['temp'] >= 65:
            temp_style = "yellow"
        else:
            temp_style = "green"
            
        temp_text = f"[{temp_style}]{gpu['temp']}°C[/{temp_style}]"
        fan_text = f"{gpu['fan_speed']}%" if isinstance(gpu['fan_speed'], int) else "[dim]N/A[/dim]"

        power_bar = ProgressBar(total=100, completed=gpu["power_percent"], width=20)
        power_text = Text.assemble(
            f"{gpu['power_usage']:.1f}W / {gpu['power_limit']:.0f}W\n",
            power_bar
        )

        mem_bar = ProgressBar(total=100, completed=gpu["mem_percent"], width=20)
        mem_text = Text.assemble(
            f"{gpu['mem_used']:.0f}MiB / {gpu['mem_total']:.0f}MiB\n",
            mem_bar
        )

        gpu_util_bar = ProgressBar(total=100, completed=gpu["gpu_util"], width=20)
        gpu_util_text = Text.assemble(
            f"{gpu['gpu_util']}%",
            "\n",
            gpu_util_bar,
        )

        table.add_row(
            str(gpu["id"]),
            gpu["name"],
            temp_text,
            fan_text,
            power_text,
            mem_text,
            gpu_util_text
        )
    
    # Add footer with driver version and timestamp
    driver_version = gpu_data[0]['driver_version'] if gpu_data else "N/A"
    footer = f"NVIDIA Driver: {driver_version} | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    return Panel(table, title="[b]GPU Status[/b]", subtitle=f"[dim]{footer}[/dim]", border_style="blue")


if __name__ == "__main__":
    console = Console()
    try:
        with Live(generate_table(get_gpu_data()), screen=True, transient=True, refresh_per_second=1) as live:
            while True:
                time.sleep(1)
                live.update(generate_table(get_gpu_data()))
    except KeyboardInterrupt:
        console.print("\n[bold green]GPU monitor stopped.[/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred: {e}[/bold red]")
